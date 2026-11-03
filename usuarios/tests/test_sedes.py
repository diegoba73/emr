"""Tests de aislamiento por sede CEHTA / ICPL."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Especialidad, Medico
from turnos.models import Recurso
from usuarios.sedes import (
    filtro_origen_lims,
    sedes_efectivas,
    usuario_tiene_capacidad,
)

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_sedes_vacias_sin_filtro_y_capacidades():
    u = User.objects.create_user(username='sec_all', password='x', rol='secretaria', sedes=[])
    assert sedes_efectivas(u) is None
    assert usuario_tiene_capacidad(u, 'guardia') is True
    assert usuario_tiene_capacidad(u, 'internacion') is True


@pytest.mark.django_db
def test_cehta_sin_guardia_ni_internacion():
    u = User.objects.create_user(
        username='sec_cehta', password='x', rol='secretaria', sedes=['CEHTA']
    )
    assert sedes_efectivas(u) == ['CEHTA']
    assert usuario_tiene_capacidad(u, 'guardia') is False
    assert usuario_tiene_capacidad(u, 'internacion') is False
    assert usuario_tiene_capacidad(u, 'recepcion') is True


@pytest.mark.django_db
def test_icpl_con_guardia_e_internacion():
    u = User.objects.create_user(
        username='sec_icpl', password='x', rol='secretaria', sedes=['ICPL']
    )
    assert usuario_tiene_capacidad(u, 'guardia') is True
    assert usuario_tiene_capacidad(u, 'internacion') is True


@pytest.mark.django_db
def test_ambas_sedes_union_capacidades():
    u = User.objects.create_user(
        username='sec_ambas', password='x', rol='secretaria', sedes=['CEHTA', 'ICPL']
    )
    assert usuario_tiene_capacidad(u, 'guardia') is True
    assert usuario_tiene_capacidad(u, 'internacion') is True


@pytest.mark.django_db
def test_filtro_origen_lims_cehta():
    origenes = filtro_origen_lims(['CEHTA'])
    assert origenes is not None
    assert 'AMBULATORIO_CEHTA' in origenes
    assert 'AMBULATORIO_ICPL' not in origenes
    assert 'GUARDIA' not in origenes


@pytest.mark.django_db
def test_recurso_filtrado_por_sede(client):
    Recurso.objects.create(nombre='Cons CEHTA', ubicacion='CEHTA', tipo_recurso='CONSULTORIO')
    Recurso.objects.create(nombre='Cons ICPL', ubicacion='ICPL', tipo_recurso='CONSULTORIO')
    user = User.objects.create_user(
        username='sec_r', password='x', rol='secretaria', sedes=['CEHTA']
    )
    client.force_authenticate(user=user)
    r = client.get('/api/recursos/')
    assert r.status_code == status.HTTP_200_OK
    payload = r.data.get('results', r.data)
    nombres = {row['nombre'] for row in payload}
    assert 'Cons CEHTA' in nombres
    assert 'Cons ICPL' not in nombres


@pytest.mark.django_db
def test_medico_filtrado_por_sede(client):
    esp = Especialidad.objects.create(nombre='Esp Sedes')
    Medico.objects.create(
        nombre='Solo', apellido='Cehta', matricula='SED-CEH-1', especialidad=esp, sedes=['CEHTA']
    )
    Medico.objects.create(
        nombre='Solo', apellido='Icpl', matricula='SED-ICP-1', especialidad=esp, sedes=['ICPL']
    )
    Medico.objects.create(
        nombre='Ambas', apellido='Clinicas', matricula='SED-AMB-1', especialidad=esp, sedes=[]
    )
    user = User.objects.create_user(
        username='sec_m', password='x', rol='secretaria', sedes=['ICPL']
    )
    client.force_authenticate(user=user)
    r = client.get('/api/medicos/')
    assert r.status_code == status.HTTP_200_OK
    payload = r.data.get('results', r.data)
    mats = {row['matricula'] for row in payload}
    assert 'SED-ICP-1' in mats
    assert 'SED-AMB-1' in mats
    assert 'SED-CEH-1' not in mats


@pytest.mark.django_db
def test_current_user_incluye_sedes(client):
    user = User.objects.create_user(
        username='sec_login',
        password='pass12345',
        rol='secretaria',
        sedes=['CEHTA'],
    )
    client.force_authenticate(user=user)
    r = client.get('/api/auth/current-user/')
    assert r.status_code == status.HTTP_200_OK
    assert r.data['sedes'] == ['CEHTA']
