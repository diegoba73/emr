"""Registro público: sin auto-vincular fichas; ambas rutas con mismas garantías."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from api.throttles import AuthRegisterThrottle
from pacientes.models import Paciente
from usuarios.serializers import PacienteRegistrationSerializer

User = get_user_model()
pytestmark = pytest.mark.django_db

MSG_NEUTRO = PacienteRegistrationSerializer.MSG_DNI_NO_AUTO_VINCULA

PAYLOAD_OK = {
    'email': 'nuevo.reg@example.com',
    'password': 'Sup3rStr0ng!Pass',
    'nombre': 'Lucia',
    'apellido': 'Nuevo',
    'dni': 'REG-SAFE-001',
    'telefono': '3511111111',
    'fecha_nacimiento': '1992-03-15',
    'obra_social': 'OSDE',
    'numero_afiliado': 'OSDE-123',
    'plan': '210',
}


@pytest.fixture(autouse=True)
def _sin_throttle_registro(monkeypatch):
    monkeypatch.setattr(AuthRegisterThrottle, 'allow_request', lambda self, request, view: True)


def client():
    return APIClient()


def test_alta_valida_auth_register():
    r = client().post('/api/auth/register/', PAYLOAD_OK, format='json')
    assert r.status_code == status.HTTP_201_CREATED, r.data
    assert 'user_id' in r.data
    user = User.objects.get(pk=r.data['user_id'])
    assert user.username == 'REG-SAFE-001'
    assert user.rol == 'paciente'
    pac = Paciente.objects.get(dni='REG-SAFE-001')
    assert pac.user_id == user.id
    assert pac.obra_social.codigo == 'OSDE'
    assert (pac.numero_afiliado or '') == 'OSDE-123'
    assert (pac.plan_obra_social or '') == '210'


def test_alta_valida_register_patient_legacy_aliases():
    r = client().post(
        '/api/auth/register/patient/',
        {
            'username': 'REG-SAFE-002',
            'email': 'legacy.reg@example.com',
            'password': 'Sup3rStr0ng!Pass',
            'first_name': 'Pedro',
            'last_name': 'Legacy',
            'dni': 'REG-SAFE-002',
            'telefono': '3512222222',
            'fecha_nacimiento': '1988-01-01',
            'obra_social': 'PARTICULAR',
        },
        format='json',
    )
    assert r.status_code == status.HTTP_201_CREATED, r.data
    pac = Paciente.objects.get(dni='REG-SAFE-002')
    assert pac.nombre.upper() == 'PEDRO'
    assert pac.apellido.upper() == 'LEGACY'
    assert pac.fecha_nacimiento is not None
    assert pac.obra_social.codigo == 'PARTICULAR'


@pytest.mark.parametrize(
    'missing',
    ['nombre', 'apellido', 'dni', 'fecha_nacimiento', 'obra_social', 'telefono', 'email', 'password'],
)
def test_campos_obligatorios_auth_register(missing):
    email = f'miss_{missing}@example.com'
    data = {**PAYLOAD_OK, 'email': email, 'dni': f'REG-MISS-{missing}'}
    data.pop(missing, None)
    r = client().post('/api/auth/register/', data, format='json')
    assert r.status_code == status.HTTP_400_BAD_REQUEST, (missing, r.data)
    assert not User.objects.filter(email=email).exists()


@pytest.mark.parametrize(
    'missing',
    ['first_name', 'last_name', 'dni', 'fecha_nacimiento', 'obra_social', 'telefono', 'email', 'password'],
)
def test_campos_obligatorios_register_patient(missing):
    email = f'leg_miss_{missing}@example.com'
    data = {
        'username': f'REG-LEG-{missing}',
        'email': email,
        'password': 'Sup3rStr0ng!Pass',
        'first_name': 'Ana',
        'last_name': 'Test',
        'dni': f'REG-LEG-{missing}',
        'telefono': '3510000000',
        'fecha_nacimiento': '1991-02-02',
        'obra_social': 'OSDE',
    }
    data.pop(missing, None)
    if missing == 'dni':
        data.pop('username', None)
    r = client().post('/api/auth/register/patient/', data, format='json')
    assert r.status_code == status.HTTP_400_BAD_REQUEST, (missing, r.data)
    assert not User.objects.filter(email=email).exists()


def test_os_sin_plan_ni_afiliado_falla():
    r = client().post(
        '/api/auth/register/',
        {
            **PAYLOAD_OK,
            'email': 'sinplan@example.com',
            'dni': 'REG-SAFE-NOPLAN',
            'obra_social': 'OSDE',
            'numero_afiliado': '',
            'plan': '',
        },
        format='json',
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    details = r.data.get('details', r.data)
    assert 'numero_afiliado' in details or 'plan' in details
    assert not Paciente.objects.filter(dni='REG-SAFE-NOPLAN').exists()


def test_no_reclama_ficha_existente_sin_user():
    from pacientes.tests.os_helpers import os_ref

    Paciente.objects.create(
        dni='REG-SAFE-FICHA',
        nombre='Ficha',
        apellido='Sola',
        fecha_nacimiento='1990-01-01',
        obra_social=os_ref('PAMI'),
    )
    assert Paciente.objects.filter(dni='REG-SAFE-FICHA', user__isnull=True).exists()

    for url in ('/api/auth/register/', '/api/auth/register/patient/'):
        data = {
            **PAYLOAD_OK,
            'email': f'claim_{url[-8:]}@example.com',
            'dni': 'REG-SAFE-FICHA',
            'telefono': '3513333333',
        }
        if url.endswith('patient/'):
            data = {
                'username': 'REG-SAFE-FICHA',
                'email': data['email'],
                'password': data['password'],
                'first_name': 'Intruso',
                'last_name': 'Claim',
                'dni': 'REG-SAFE-FICHA',
                'telefono': '3513333333',
                'fecha_nacimiento': '1990-01-01',
                'obra_social': 'PAMI',
                'numero_afiliado': 'PAMI-1',
                'plan': 'BASICO',
            }
        before_users = User.objects.count()
        r = client().post(url, data, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST, r.data
        body = str(r.data)
        assert 'REG-SAFE-FICHA' not in body or MSG_NEUTRO[:20] in body or 'details' in body
        assert User.objects.count() == before_users
        pac = Paciente.objects.get(dni='REG-SAFE-FICHA')
        assert pac.user_id is None
        assert pac.nombre.upper() == 'FICHA'


def test_falla_media_no_deja_usuario_huerfano(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('simulated paciente create failure')

    monkeypatch.setattr(Paciente.objects, 'create', boom)
    before = User.objects.count()
    r = client().post(
        '/api/auth/register/',
        {**PAYLOAD_OK, 'email': 'huerfano@example.com', 'dni': 'REG-SAFE-HUE'},
        format='json',
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.count() == before
    assert not Paciente.objects.filter(dni='REG-SAFE-HUE').exists()


@pytest.mark.skipif(connection.vendor != 'postgresql', reason='select_for_update / unique race en Postgres')
def test_alta_concurrente_mismo_dni_postgres():
    """Ambas altas del mismo DNI: como máximo una cuenta; la otra falla sin huérfanos."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    payloads = [
        {**PAYLOAD_OK, 'email': 'race0@example.com', 'dni': 'REG-SAFE-RACE'},
        {**PAYLOAD_OK, 'email': 'race1@example.com', 'dni': 'REG-SAFE-RACE'},
    ]

    def _post(data):
        return client().post('/api/auth/register/', data, format='json').status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = [f.result() for f in as_completed([pool.submit(_post, p) for p in payloads])]
    assert codes.count(201) <= 1
    assert Paciente.objects.filter(dni='REG-SAFE-RACE').count() <= 1
    assert User.objects.filter(username='REG-SAFE-RACE').count() <= 1
