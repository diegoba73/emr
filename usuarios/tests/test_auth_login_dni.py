"""Login por DNI aunque User.username != Paciente.dni (alta secretaría)."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.models import Paciente
from usuarios.auth_login import normalize_login_identifier, username_candidates

User = get_user_model()


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_normalize_dni_quita_puntos_y_espacios():
    assert normalize_login_identifier(' 30.123.456 ') == '30123456'
    assert normalize_login_identifier('30123456') == '30123456'
    assert normalize_login_identifier('secretaria1') == 'secretaria1'


@pytest.mark.django_db
def test_login_con_dni_cuando_username_es_otro(api):
    user = User.objects.create_user(
        username='jperez_portal',
        email='jperez_portal@test.com',
        password='ClaveSegura1',
        rol='paciente',
    )
    Paciente.objects.create(
        user=user,
        dni='30123456',
        nombre='Juan',
        apellido='Perez',
        obra_social='OSDE',
    )
    r = api.post(
        '/api/auth/login/',
        {'username': '30123456', 'password': 'ClaveSegura1'},
        format='json',
    )
    assert r.status_code == status.HTTP_200_OK, r.data
    assert r.data['user']['username'] == 'jperez_portal'
    assert r.data['user']['rol'] == 'PACIENTE'


@pytest.mark.django_db
def test_login_con_dni_con_puntos(api):
    user = User.objects.create_user(
        username='30111222',
        email='dni_puntos@test.com',
        password='ClaveSegura1',
        rol='paciente',
    )
    Paciente.objects.create(
        user=user,
        dni='30111222',
        nombre='Ana',
        apellido='Diaz',
        obra_social='PAMI',
    )
    r = api.post(
        '/api/auth/login/',
        {'username': '30.111.222', 'password': 'ClaveSegura1'},
        format='json',
    )
    assert r.status_code == status.HTTP_200_OK, r.data


@pytest.mark.django_db
def test_login_username_igual_dni_sigue_ok(api):
    user = User.objects.create_user(
        username='30999888',
        email='dni_igual@test.com',
        password='ClaveSegura1',
        rol='paciente',
    )
    Paciente.objects.create(
        user=user,
        dni='30999888',
        nombre='Luis',
        apellido='Gomez',
        obra_social='OSDE',
    )
    r = api.post(
        '/api/auth/login/',
        {'username': '30999888', 'password': 'ClaveSegura1'},
        format='json',
    )
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_login_password_incorrecta_no_enumera(api):
    user = User.objects.create_user(
        username='otro_user',
        email='otro_user@test.com',
        password='ClaveSegura1',
        rol='paciente',
    )
    Paciente.objects.create(
        user=user,
        dni='30888777',
        nombre='Eva',
        apellido='Ruiz',
        obra_social='OSDE',
    )
    r = api.post(
        '/api/auth/login/',
        {'username': '30888777', 'password': 'mala'},
        format='json',
    )
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'inválidas' in (r.data.get('error') or '').lower()


@pytest.mark.django_db
def test_alta_staff_paciente_fuerza_username_igual_dni(api):
    staff = User.objects.create_user(
        username='sec_dni',
        email='sec_dni@test.com',
        password='ClaveSegura1',
        rol='admin',
        is_staff=True,
        is_superuser=True,
    )
    api.force_authenticate(user=staff)
    r = api.post(
        '/api/usuarios/users/',
        {
            'username': 'nombre_libre',
            'email': 'nuevo_pac@test.com',
            'password': 'ClaveSegura1',
            'password_confirm': 'ClaveSegura1',
            'first_name': 'Nora',
            'last_name': 'Salas',
            'rol': 'paciente',
            'paciente_data': {
                'dni': '30777666',
                'fecha_nacimiento': '1990-01-15',
                'obra_social': 'OSDE',
            },
        },
        format='json',
    )
    assert r.status_code == status.HTTP_201_CREATED, r.data
    created = User.objects.get(email='nuevo_pac@test.com')
    assert created.username == '30777666'
    assert Paciente.objects.get(dni='30777666').user_id == created.id


@pytest.mark.django_db
def test_username_candidates_incluye_user_vinculado():
    user = User.objects.create_user(
        username='alias_x',
        email='alias_x@test.com',
        password='ClaveSegura1',
        rol='paciente',
    )
    Paciente.objects.create(user=user, dni='30555444', nombre='A', apellido='B')
    cands = username_candidates('30.555.444')
    assert 'alias_x' in cands
    assert '30555444' in cands
