"""QA-ROLE-01 — permisos por rol en GET/POST/PATCH /api/atenciones/."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno

User = get_user_model()


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def especialidad(db):
    return Especialidad.objects.get_or_create(nombre='General')[0]


@pytest.fixture
def recurso(db):
    uid = _uid()
    return Recurso.objects.create(
        nombre=f'Consultorio {uid}',
        ubicacion='Piso 1',
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )


@pytest.fixture
def paciente(db):
    uid = _uid()
    user = User.objects.create_user(
        username=f'pac_{uid}',
        email=f'pac_{uid}@test.com',
        password='x',
        rol='paciente',
    )
    return Paciente.objects.create(
        user=user,
        dni=f'DNI{uid}',
        nombre='Ana',
        apellido='Paciente',
        fecha_nacimiento='1990-01-01',
    )


@pytest.fixture
def medico_a(db, especialidad):
    uid = _uid()
    user = User.objects.create_user(
        username=f'med_a_{uid}',
        email=f'med_a_{uid}@test.com',
        password='x',
        rol='medico',
    )
    med = Medico.objects.create(
        user=user,
        matricula=f'MA{uid}',
        nombre='Med',
        apellido='A',
        especialidad=especialidad,
    )
    return user, med


@pytest.fixture
def medico_b(db, especialidad):
    uid = _uid()
    user = User.objects.create_user(
        username=f'med_b_{uid}',
        email=f'med_b_{uid}@test.com',
        password='x',
        rol='medico',
    )
    med = Medico.objects.create(
        user=user,
        matricula=f'MB{uid}',
        nombre='Med',
        apellido='B',
        especialidad=especialidad,
    )
    return user, med


@pytest.fixture
def atencion_medico_a(paciente, medico_a, recurso):
    user_a, med_a = medico_a
    base = timezone.now() + timedelta(hours=2)
    turno = Turno.objects.create(
        paciente=paciente,
        medico=med_a,
        recurso=recurso,
        fecha_hora_inicio=base,
        fecha_hora_fin=base + timedelta(hours=1),
        estado='CONFIRMADO',
    )
    return Atencion.objects.create(
        turno=turno,
        paciente=paciente,
        medico_principal=med_a,
        tipo_atencion=recurso.tipo_recurso,
        tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        estado_clinico=Atencion.EstadoClinico.ABIERTA,
    )


@pytest.fixture
def atencion_medico_b(db, especialidad, recurso):
    uid = _uid()
    user_b = User.objects.create_user(
        username=f'med_b_{uid}',
        email=f'med_b_{uid}@test.com',
        password='x',
        rol='medico',
    )
    med_b = Medico.objects.create(
        user=user_b,
        matricula=f'MB{uid}',
        nombre='Med',
        apellido='B',
        especialidad=especialidad,
    )
    user_pac = User.objects.create_user(
        username=f'pac_b_{uid}',
        email=f'pac_b_{uid}@test.com',
        password='x',
        rol='paciente',
    )
    paciente_b = Paciente.objects.create(
        user=user_pac,
        dni=f'DNIB{uid}',
        nombre='Otro',
        apellido='Paciente',
        fecha_nacimiento='1991-01-01',
    )
    base = timezone.now() + timedelta(hours=4)
    turno = Turno.objects.create(
        paciente=paciente_b,
        medico=med_b,
        recurso=recurso,
        fecha_hora_inicio=base,
        fecha_hora_fin=base + timedelta(hours=1),
        estado='CONFIRMADO',
    )
    return Atencion.objects.create(
        turno=turno,
        paciente=paciente_b,
        medico_principal=med_b,
        tipo_atencion=recurso.tipo_recurso,
        tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        estado_clinico=Atencion.EstadoClinico.ABIERTA,
    )


def _user(rol: str, suffix: str | None = None) -> User:
    uid = suffix or _uid()
    return User.objects.create_user(
        username=f'{rol}_{uid}',
        email=f'{rol}_{uid}@test.com',
        password='x',
        rol=rol,
    )


@pytest.mark.django_db
class TestAtencionPermissionsList:
    def test_anonimo_bloqueado(self, client):
        response = client.get(reverse('atenciones-list'))
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_sin_rol_bloqueado(self, client):
        user = User.objects.create_user(
            username=f'sinrol_{_uid()}',
            email='sinrol@test.com',
            password='x',
            rol='otro',
        )
        client.force_authenticate(user=user)
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_bloqueado(self, client):
        client.force_authenticate(user=_user('laboratorio'))
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_secretaria_bloqueada(self, client, atencion_medico_a):
        client.force_authenticate(user=_user('secretaria'))
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_enfermeria_lectura_global(self, client, atencion_medico_a, atencion_medico_b):
        client.force_authenticate(user=_user('enfermeria'))
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert atencion_medico_a.id in ids
        assert atencion_medico_b.id in ids

    def test_paciente_solo_propias(self, client, paciente, atencion_medico_a, atencion_medico_b):
        client.force_authenticate(user=paciente.user)
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert atencion_medico_a.id in ids
        assert len(ids) == 1

    def test_medico_solo_propias(self, client, medico_a, medico_b, atencion_medico_a, atencion_medico_b):
        client.force_authenticate(user=medico_a[0])
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert atencion_medico_a.id in ids
        assert atencion_medico_b.id not in ids

    def test_admin_ve_todas(self, client, atencion_medico_a, atencion_medico_b):
        admin = _user('admin')
        client.force_authenticate(user=admin)
        response = client.get(reverse('atenciones-list'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 2


@pytest.mark.django_db
class TestAtencionPermissionsMutations:
    def test_paciente_no_puede_patch(self, client, paciente, atencion_medico_a):
        client.force_authenticate(user=paciente.user)
        url = reverse('atenciones-detail', args=[atencion_medico_a.id])
        response = client.patch(url, {'observaciones_generales': 'x'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_enfermeria_no_puede_patch(self, client, atencion_medico_a):
        client.force_authenticate(user=_user('enfermeria'))
        url = reverse('atenciones-detail', args=[atencion_medico_a.id])
        response = client.patch(url, {'observaciones_generales': 'x'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_secretaria_no_puede_post(self, client, atencion_medico_a):
        client.force_authenticate(user=_user('secretaria'))
        response = client.post(
            reverse('atenciones-list'),
            {'turno': atencion_medico_a.turno_id},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_medico_no_ve_ni_opera_ajena(
        self, client, medico_a, atencion_medico_b
    ):
        client.force_authenticate(user=medico_a[0])
        url = reverse('atenciones-detail', args=[atencion_medico_b.id])
        assert client.get(url).status_code == status.HTTP_404_NOT_FOUND
        assert client.patch(url, {'observaciones_generales': 'x'}, format='json').status_code == status.HTTP_404_NOT_FOUND

    def test_medico_puede_cerrar_propia(self, client, medico_a, atencion_medico_a):
        client.force_authenticate(user=medico_a[0])
        url = reverse('atenciones-cerrar', args=[atencion_medico_a.id])
        response = client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_enfermeria_no_puede_cerrar(self, client, atencion_medico_a):
        client.force_authenticate(user=_user('enfermeria'))
        url = reverse('atenciones-cerrar', args=[atencion_medico_a.id])
        response = client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
