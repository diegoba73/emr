"""Tests de roles profesionales de estudios complementarios."""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from estudios.models import EstudioComplementario, TipoEstudioComplementario
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno
from usuarios.models import User
from usuarios.serializers import UserSerializer

BASE = '/api/estudios-complementarios/'


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def paciente(db):
    u = User.objects.create_user(username=f'pac_{_uid()}', password='x', rol='paciente')
    return Paciente.objects.create(user=u, dni=f'DNI{_uid()}', nombre='Ana', apellido='Test')


@pytest.fixture
def medico(db):
    u = User.objects.create_user(username=f'med_{_uid()}', password='x', rol='medico')
    return Medico.objects.create(user=u, matricula=f'M{_uid()}', nombre='Dr', apellido='Test')


@pytest.fixture
def recurso(db):
    return Recurso.objects.create(
        nombre=f'Cons {_uid()}',
        ubicacion='CEHTA',
        tipo_recurso='CONSULTORIO',
        activo=True,
    )


@pytest.fixture
def tipo_estudio(db):
    return TipoEstudioComplementario.objects.create(
        nombre='RX Tórax',
        modalidad=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
    )


@pytest.fixture
def estudio_solicitado(paciente, tipo_estudio, medico):
    admin = User.objects.create_user(username=f'adm_{_uid()}', password='x', rol='admin')
    return EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        estado=EstudioComplementario.Estado.SOLICITADO,
        medico_solicitante=medico,
        creado_por=admin,
    )


@pytest.mark.django_db
class TestRolesEstudioComplementario:
    @pytest.fixture
    def radiologo(self, db):
        return User.objects.create_user(
            username='radio1',
            email='radio1@test.com',
            password='x',
            rol='radiologo',
        )

    def test_radiologo_lista_estudios(self, client, radiologo, estudio_solicitado):
        client.force_authenticate(user=radiologo)
        r = client.get(BASE)
        assert r.status_code == 200
        items = r.data.get('results', r.data)
        assert len(items) >= 1

    def test_radiologo_crea_estudio(self, client, radiologo, paciente, tipo_estudio):
        client.force_authenticate(user=radiologo)
        payload = {
            'paciente_id': paciente.id,
            'tipo_estudio': tipo_estudio.id,
            'modalidad': tipo_estudio.modalidad,
            'origen': 'INTERNO',
            'descripcion_clinica': 'Control',
        }
        r = client.post(BASE, payload, format='json')
        assert r.status_code == 201, r.data

    def test_radiologo_lista_pacientes(self, client, radiologo, paciente):
        client.force_authenticate(user=radiologo)
        r = client.get('/api/pacientes/')
        assert r.status_code == 200
        assert len(r.data['results']) >= 1

    def test_kinesiologo_ve_turnos(self, client, paciente, medico, recurso):
        kine = User.objects.create_user(
            username='kine1',
            email='kine1@test.com',
            password='x',
            rol='kinesiologo',
        )
        Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=timezone.now() + timedelta(days=1),
            fecha_hora_fin=timezone.now() + timedelta(days=1, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        client.force_authenticate(user=kine)
        r = client.get('/api/turnos/')
        assert r.status_code == 200
        assert len(r.data['results']) == 1

    def test_user_serializer_acepta_roles_estudio(self):
        for rol in ('kinesiologo', 'radiologo', 'ecografista', 'fonoaudiologo'):
            data = {
                'username': f'user_{rol}_{_uid()}',
                'email': f'{rol}_{_uid()}@test.com',
                'password': 'StrongP@ssw0rd!',
                'password_confirm': 'StrongP@ssw0rd!',
                'rol': rol,
                'first_name': 'Pro',
                'last_name': 'Test',
                'is_active': True,
            }
            serializer = UserSerializer(data=data)
            assert serializer.is_valid(), serializer.errors
