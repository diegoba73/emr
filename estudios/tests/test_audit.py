"""Tests de auditoría — estudios complementarios."""

from __future__ import annotations

import pytest

from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from estudios.tests.conftest import _payload_crear

BASE = '/api/estudios-complementarios/'


@pytest.mark.django_db
def test_create_estudio_auditado(client, admin_user, paciente, tipo_estudio):
    client.force_authenticate(user=admin_user)
    with capture_on_commit_callbacks(execute=True):
        r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    assert r.status_code == 201
    evs = [
        e for e in AuditEvent.objects.filter(module='estudios').order_by('-id')[:20]
        if (e.metadata or {}).get('accion') == 'estudio_complementario_create'
    ]
    ev = evs[0] if evs else None
    assert ev is not None
    assert ev.entity_repr.startswith('estudios.EstudioComplementario:')
    assert '/media/' not in str(ev.metadata)


@pytest.mark.django_db
def test_estado_cambio_auditado(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    with capture_on_commit_callbacks(execute=True):
        client.post(f'{BASE}{estudio_solicitado.id}/marcar-realizado/')
    evs = [e for e in AuditEvent.objects.filter(module='estudios').order_by('-id')[:20]
           if (e.metadata or {}).get('accion') == 'estudio_estado_cambio']
    ev = evs[0] if evs else None
    assert ev is not None
    assert ev.metadata.get('estado_anterior') == 'SOLICITADO'
    assert ev.metadata.get('estado_nuevo') == 'REALIZADO'
    assert '/media/' not in str(ev.metadata)


@pytest.mark.django_db
def test_informe_snapshot_sin_texto_completo(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    texto_largo = 'X' * 5000
    eid = estudio_solicitado.id
    with capture_on_commit_callbacks(execute=True):
        client.post(f'{BASE}{eid}/informes/', {'texto': texto_largo}, format='json')
    evs = [e for e in AuditEvent.objects.filter(module='estudios').order_by('-id')[:20]
           if (e.metadata or {}).get('accion') == 'estudio_informe_create']
    ev = evs[0] if evs else None
    assert ev is not None
    after = ev.after_state or {}
    assert after.get('texto') != texto_largo
