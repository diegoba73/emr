"""Tests — sugerencia de informe de estudio complementario (nivel 1)."""

from __future__ import annotations

import pytest
from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from estudios.models import EstudioComplementario, InformeEstudioComplementario
from estudios.sugerir_informe import construir_informe_estudio_reglas, sugerir_informe_estudio

BASE = '/api/estudios-complementarios/'


@pytest.mark.django_db
def test_construir_informe_reglas_incluye_modalidad(estudio_solicitado):
    estudio_solicitado.descripcion_clinica = 'Tos y fiebre'
    estudio_solicitado.save(update_fields=['descripcion_clinica'])
    data = construir_informe_estudio_reglas(estudio_solicitado, notas_medico='Sin infiltrados')
    assert data['fuente'] == 'reglas'
    assert data['marcado_sugerencia'] is True
    assert 'Rayos X' in data['texto'] or 'IMAGEN_RX' in data['texto'] or 'Modalidad' in data['texto']
    assert 'Tos y fiebre' in data['texto']
    assert 'Sin infiltrados' in data['texto']
    assert 'sugerencia asistida' in data['texto'].lower()


@pytest.mark.django_db
def test_sugerir_informe_sin_medgemma_usa_reglas(estudio_solicitado, settings):
    settings.MEDGEMMA_ENABLED = False
    data = sugerir_informe_estudio(estudio_solicitado, prefer_medgemma=True)
    assert data['fuente'] == 'reglas'
    assert data['texto']


@pytest.mark.django_db
def test_api_sugerir_informe_no_persiste(client, admin_user, estudio_solicitado, settings):
    settings.MEDGEMMA_ENABLED = False
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    client.post(f'{BASE}{eid}/marcar-realizado/')
    with capture_on_commit_callbacks(execute=True):
        r = client.post(
            f'{BASE}{eid}/sugerir-informe/',
            {'notas_medico': 'Control normal', 'prefer_medgemma': False},
            format='json',
        )
    assert r.status_code == 200
    assert r.data['texto']
    assert r.data['marcado_sugerencia'] is True
    assert InformeEstudioComplementario.objects.filter(estudio_id=eid).count() == 0
    evs = [
        e
        for e in AuditEvent.objects.filter(module='estudios').order_by('-id')[:20]
        if (e.metadata or {}).get('accion') == 'estudio_informe_sugerir'
    ]
    assert len(evs) >= 1
    assert 'texto' not in (evs[0].metadata or {})


@pytest.mark.django_db
def test_api_sugerir_informe_solo_realizado(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    r = client.post(
        f'{BASE}{estudio_solicitado.id}/sugerir-informe/',
        {'prefer_medgemma': False},
        format='json',
    )
    assert r.status_code == 400
    assert estudio_solicitado.estado == EstudioComplementario.Estado.SOLICITADO
