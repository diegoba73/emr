"""API catálogo quirúrgico jerárquico — permisos y filtros.

Fuera de laboratorio/: no toca LIMS.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from catalogos.models import CirugiaAbordaje, CirugiaEspecialidad, CirugiaProcedimiento

User = get_user_model()


def _uid() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture
def admin_client(db):
    user = User.objects.create_user(
        username=f'cir_adm_{_uid()}',
        password='test-pass-123',
        rol='admin',
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def medico_client(db):
    user = User.objects.create_user(
        username=f'cir_med_{_uid()}',
        password='test-pass-123',
        rol='medico',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def secretaria_client(db):
    user = User.objects.create_user(
        username=f'cir_sec_{_uid()}',
        password='test-pass-123',
        rol='secretaria',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def tree(db):
    esp = CirugiaEspecialidad.objects.create(nombre=f'Esp {_uid()}', activo=True, orden=10)
    proc = CirugiaProcedimiento.objects.create(
        especialidad=esp, nombre=f'Proc {_uid()}', activo=True,
    )
    abr = CirugiaAbordaje.objects.create(
        procedimiento=proc, nombre=f'Abr {_uid()}', activo=True,
    )
    return {'especialidad': esp, 'procedimiento': proc, 'abordaje': abr}


@pytest.mark.django_db
def test_list_filtra_por_especialidad_y_activo(admin_client, tree):
    CirugiaEspecialidad.objects.create(nombre=f'Otra {_uid()}', activo=False, orden=20)
    r = admin_client.get('/api/cirugia-especialidades/', {'activo': 'true'})
    assert r.status_code == 200
    rows = r.data if isinstance(r.data, list) else r.data.get('results', [])
    assert all(x.get('activo', True) for x in rows)
    assert any(x['id'] == tree['especialidad'].id for x in rows)

    r2 = admin_client.get(
        '/api/cirugia-procedimientos/',
        {'especialidad': tree['especialidad'].id, 'activo': 'true'},
    )
    assert r2.status_code == 200
    procs = r2.data if isinstance(r2.data, list) else r2.data.get('results', [])
    assert len(procs) == 1
    assert procs[0]['id'] == tree['procedimiento'].id

    r3 = admin_client.get(
        '/api/cirugia-abordajes/',
        {'procedimiento': tree['procedimiento'].id},
    )
    assert r3.status_code == 200
    abrs = r3.data if isinstance(r3.data, list) else r3.data.get('results', [])
    assert any(x['id'] == tree['abordaje'].id for x in abrs)


@pytest.mark.django_db
def test_write_admin_ok_medico_y_secretaria_denegados(admin_client, medico_client, secretaria_client):
    nombre = f'Esp write {_uid()}'
    r = admin_client.post(
        '/api/cirugia-especialidades/',
        {'nombre': nombre, 'activo': True, 'orden': 1},
        format='json',
    )
    assert r.status_code in (200, 201), r.data
    pk = r.data['id']

    r_med = medico_client.post(
        '/api/cirugia-especialidades/',
        {'nombre': f'Esp med {_uid()}', 'activo': True},
        format='json',
    )
    assert r_med.status_code in (403, 401)

    r_sec = secretaria_client.patch(
        f'/api/cirugia-especialidades/{pk}/',
        {'nombre': f'Renamed {_uid()}'},
        format='json',
    )
    assert r_sec.status_code in (403, 401)

    r_list = medico_client.get('/api/cirugia-especialidades/', {'activo': 'true'})
    assert r_list.status_code == 200


@pytest.mark.django_db
def test_poblar_cirugias_catalogo_dry_run(db, capsys):
    call_command('poblar_cirugias_catalogo', dry_run=True)
    out = capsys.readouterr().out
    assert '[dry-run]' in out
    assert 'especialidades' in out
    assert CirugiaEspecialidad.objects.count() == 0
