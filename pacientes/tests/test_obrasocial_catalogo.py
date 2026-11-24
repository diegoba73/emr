"""Catálogo ObraSocial: seed, resolve, API, registro y backfill legacy."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.models import ObraSocial, Paciente, PacienteAfiliacion
from pacientes.obras_sociales import ensure_seed_obras_sociales, resolve_obra_social

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def seed_os():
    ensure_seed_obras_sociales()


def test_seed_incluye_particular(seed_os):
    assert ObraSocial.objects.filter(codigo='PARTICULAR', activo=True).exists()
    assert ObraSocial.objects.filter(codigo='SEROS').exists()


def test_resolve_codigo_y_legacy(seed_os):
    assert resolve_obra_social('particular').codigo == 'PARTICULAR'
    legacy = resolve_obra_social('Mi OS Inventada XYZ', create_legacy=True)
    assert legacy is not None
    assert legacy.codigo.startswith('MI_OS')
    assert resolve_obra_social('NO_EXISTE_XYZ') is None


def test_api_catalogo_publico(seed_os):
    r = APIClient().get('/api/obras-sociales/')
    assert r.status_code == 200
    codigos = {x['codigo'] for x in r.data}
    assert 'PARTICULAR' in codigos


def test_alta_paciente_con_codigo(seed_os):
    admin = User.objects.create_user(username='os_admin', password='x', rol='admin', is_staff=True)
    c = APIClient()
    c.force_authenticate(user=admin)
    r = c.post(
        '/api/pacientes/',
        {
            'dni': 'OS-CAT-001',
            'nombre': 'Ana',
            'apellido': 'Os',
            'fecha_nacimiento': '1990-01-01',
            'obra_social': 'PARTICULAR',
        },
        format='json',
    )
    assert r.status_code == status.HTTP_201_CREATED, r.data
    assert r.data['obra_social'] == 'PARTICULAR'
    assert r.data['obra_social_id']
    pac = Paciente.objects.get(dni='OS-CAT-001')
    assert pac.obra_social.codigo == 'PARTICULAR'


def test_registro_publico_particular(seed_os):
    from api.throttles import AuthRegisterThrottle
    import usuarios.tests.test_registro_publico_seguro as mod

    # throttle already patched in other module; patch here too
    AuthRegisterThrottle.allow_request = lambda self, request, view: True  # type: ignore
    r = APIClient().post(
        '/api/auth/register/',
        {
            'email': 'os.reg@example.com',
            'password': 'Sup3rStr0ng!Pass',
            'nombre': 'Reg',
            'apellido': 'Os',
            'dni': 'OS-REG-99',
            'telefono': '3519999999',
            'fecha_nacimiento': '1991-05-05',
            'obra_social': 'PARTICULAR',
        },
        format='json',
    )
    assert r.status_code == status.HTTP_201_CREATED, r.data
    pac = Paciente.objects.get(dni='OS-REG-99')
    assert pac.obra_social.codigo == 'PARTICULAR'


def test_registro_codigo_invalido_400(seed_os):
    from api.throttles import AuthRegisterThrottle

    AuthRegisterThrottle.allow_request = lambda self, request, view: True  # type: ignore
    r = APIClient().post(
        '/api/auth/register/',
        {
            'email': 'os.bad@example.com',
            'password': 'Sup3rStr0ng!Pass',
            'nombre': 'Bad',
            'apellido': 'Os',
            'dni': 'OS-BAD-01',
            'telefono': '3518888888',
            'fecha_nacimiento': '1991-05-05',
            'obra_social': 'NO_EXISTE_XYZ',
        },
        format='json',
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST


def test_afiliacion_fk(seed_os):
    osde = ObraSocial.objects.get(codigo='OSDE')
    pac = Paciente.objects.create(
        dni='OS-AFIL-1',
        nombre='Afil',
        apellido='Test',
        fecha_nacimiento='1985-01-01',
        obra_social=osde,
    )
    afil = PacienteAfiliacion.objects.create(
        paciente=pac,
        obra_social=osde,
        numero_afiliado='123',
        es_principal=True,
        activo=True,
    )
    assert afil.obra_social.codigo == 'OSDE'


def test_movil_register_y_obras(seed_os):
    from api.throttles import AuthRegisterThrottle

    AuthRegisterThrottle.allow_request = lambda self, request, view: True  # type: ignore
    c = APIClient()
    r = c.get('/api/movil/obras-sociales/')
    assert r.status_code == 200
    assert any(x['codigo'] == 'PARTICULAR' for x in r.data)
    r2 = c.post(
        '/api/movil/auth/register/',
        {
            'email': 'os.movil@example.com',
            'password': 'Sup3rStr0ng!Pass',
            'nombre': 'Mov',
            'apellido': 'Il',
            'dni': 'OS-MOV-01',
            'telefono': '3517777777',
            'fecha_nacimiento': '1993-03-03',
            'obra_social': 'PAMI',
            'numero_afiliado': 'PAMI-99',
            'plan': 'BASICO',
        },
        format='json',
    )
    assert r2.status_code == status.HTTP_201_CREATED, r2.data
    pac = Paciente.objects.get(dni='OS-MOV-01')
    assert pac.obra_social.codigo == 'PAMI'
    assert (pac.plan_obra_social or '') == 'BASICO'
