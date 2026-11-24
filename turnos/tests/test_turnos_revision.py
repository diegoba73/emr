"""GET /api/turnos/revision/ — stamp liviano para sync multi-cliente."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno

User = get_user_model()


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


def _recurso(suffix: str) -> Recurso:
    return Recurso.objects.create(
        nombre=f'Cons Rev {suffix}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )


@pytest.mark.django_db
class TestTurnosRevision(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Revision')
        cls.paciente = Paciente.objects.create(
            dni='TE-REV-1', nombre='Pac', apellido='Rev',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Rev', matricula='TE-REV-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('rev')
        cls.secretaria = User.objects.create_user(
            username='te_rev_sec',
            email='te_rev_sec@test.com',
            password='x',
            rol='secretaria',
        )

    def _crear_turno(self, suffix: int) -> Turno:
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=24 + suffix)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )

    def test_anonimo_401(self):
        r = self.client.get('/api/turnos/revision/')
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_vacio_devuelve_cero(self):
        self.client.force_authenticate(user=self.secretaria)
        r = self.client.get('/api/turnos/revision/')
        assert r.status_code == status.HTTP_200_OK
        assert r.data['revision'] == '0|0'

    def test_cambia_al_crear_y_al_actualizar(self):
        self.client.force_authenticate(user=self.secretaria)
        r0 = self.client.get('/api/turnos/revision/')
        assert r0.status_code == status.HTTP_200_OK
        assert r0.data['revision'] == '0|0'

        t = self._crear_turno(1)
        r1 = self.client.get('/api/turnos/revision/')
        assert r1.status_code == status.HTTP_200_OK
        rev1 = r1.data['revision']
        assert rev1 != '0|0'
        assert rev1.endswith('|1')

        t.estado = Turno.Estado.CONFIRMADO
        t.save(update_fields=['estado', 'updated_at'])
        r2 = self.client.get('/api/turnos/revision/')
        assert r2.status_code == status.HTTP_200_OK
        rev2 = r2.data['revision']
        assert rev2 != rev1
        assert rev2.endswith('|1')

        self._crear_turno(2)
        r3 = self.client.get('/api/turnos/revision/')
        assert r3.status_code == status.HTTP_200_OK
        assert r3.data['revision'].endswith('|2')
        assert r3.data['revision'] != rev2


@pytest.mark.django_db
class TestTurnosRevisionMovil(APITestCase):
    """Misma acción heredada en TurnosMovil, expuesta en /api/movil/turnos/revision/."""

    def test_movil_revision_ok(self):
        from django.core.cache import cache

        cache.clear()
        especialidad = _esp('Cardiología Rev Movil')
        user = User.objects.create_user(
            username='te_rev_pac',
            email='te_rev_pac@test.com',
            password='test-password',
            rol='paciente',
        )
        paciente = Paciente.objects.create(
            user=user, dni='TE-REV-M1', nombre='Pac', apellido='Mov',
        )
        medico = Medico.objects.create(
            nombre='Dr', apellido='Mov', matricula='TE-REV-MM', especialidad=especialidad,
        )
        recurso = _recurso('revm')

        login = self.client.post(
            '/api/movil/login/',
            {'username': user.username, 'password': 'test-password'},
            format='json',
        )
        assert login.status_code == status.HTTP_200_OK, login.data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

        r = self.client.get('/api/movil/turnos/revision/')
        assert r.status_code == status.HTTP_200_OK
        assert 'revision' in r.data
        assert r.data['revision'] == '0|0'

        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=30)
        Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )
        r2 = self.client.get('/api/movil/turnos/revision/')
        assert r2.status_code == status.HTTP_200_OK
        assert r2.data['revision'].endswith('|1')
