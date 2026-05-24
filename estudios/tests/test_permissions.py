"""Tests de permisos — estudios complementarios."""

from __future__ import annotations

import pytest

from estudios.tests.conftest import _payload_crear

BASE = '/api/estudios-complementarios/'


@pytest.mark.django_db
def test_usuario_sin_rol_no_lista(client, db, paciente, tipo_estudio):
    u = __import__('usuarios.models', fromlist=['User']).User.objects.create_user(
        username='norol_x', password='x',
    )
    client.force_authenticate(user=u)
    r = client.get(BASE)
    assert r.status_code in (403, 401, 200)
    if r.status_code == 200:
        items = r.data.get('results', r.data)
        assert len(items) == 0


@pytest.mark.django_db
def test_laboratorio_sin_acceso(client, db, estudio_solicitado):
    from usuarios.models import User

    u = User.objects.create_user(username='lab_x', password='x', rol='laboratorio')
    client.force_authenticate(user=u)
    r = client.get(f'{BASE}{estudio_solicitado.id}/')
    assert r.status_code in (403, 404)
