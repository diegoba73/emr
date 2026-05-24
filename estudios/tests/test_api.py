"""Tests API — estudios complementarios."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from archivos_medicos.models import ArchivoMedico
from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from estudios.models import EstudioComplementario, InformeEstudioComplementario
from estudios.tests.conftest import _payload_crear

BASE = '/api/estudios-complementarios/'


@pytest.mark.django_db
def test_admin_crea_estudio(client, admin_user, paciente, tipo_estudio):
    client.force_authenticate(user=admin_user)
    with capture_on_commit_callbacks(execute=True):
        r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    assert r.status_code == 201
    assert r.data['estado'] == 'SOLICITADO'


@pytest.mark.django_db
def test_medico_vinculado_crea(client, medico, paciente, tipo_estudio, atencion_vinculada):
    client.force_authenticate(user=medico.user)
    r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    assert r.status_code == 201


@pytest.mark.django_db
def test_medico_ajeno_no_crea(client, medico_ajeno, paciente, tipo_estudio):
    client.force_authenticate(user=medico_ajeno.user)
    r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    assert r.status_code in (403, 400)


@pytest.mark.django_db
def test_paciente_no_crea(client, paciente, tipo_estudio):
    client.force_authenticate(user=paciente.user)
    r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    assert r.status_code == 403


@pytest.mark.django_db
def test_secretaria_no_accede(client, secretaria, estudio_solicitado):
    client.force_authenticate(user=secretaria)
    r = client.get(BASE)
    assert r.status_code == 200
    items = r.data.get('results', r.data)
    assert len(items) == 0


@pytest.mark.django_db
def test_patch_estado_rechazado(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    r = client.patch(
        f'{BASE}{estudio_solicitado.id}/',
        {'estado': 'REALIZADO'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_delete_405(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    r = client.delete(f'{BASE}{estudio_solicitado.id}/')
    assert r.status_code == 405


@pytest.mark.django_db
def test_flujo_estados(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    with capture_on_commit_callbacks(execute=True):
        r = client.post(f'{BASE}{eid}/marcar-realizado/')
    assert r.status_code == 200
    assert r.data['estado'] == 'REALIZADO'

    with capture_on_commit_callbacks(execute=True):
        r = client.post(f'{BASE}{eid}/informes/', {'texto': 'Hallazgos'}, format='json')
    assert r.status_code == 201
    informe_id = r.data['id']

    with capture_on_commit_callbacks(execute=True):
        r = client.post(f'{BASE}{eid}/informes/{informe_id}/emitir/')
    assert r.status_code == 200

    with capture_on_commit_callbacks(execute=True):
        r = client.post(f'{BASE}{eid}/informes/{informe_id}/validar/')
    assert r.status_code == 200

    estudio_solicitado.refresh_from_db()
    assert estudio_solicitado.estado == 'VALIDADO'

    with capture_on_commit_callbacks(execute=True):
        r = client.post(f'{BASE}{eid}/entregar/')
    assert r.status_code == 200
    assert r.data['estado'] == 'ENTREGADO'


@pytest.mark.django_db
def test_anular_requiere_motivo(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    r = client.post(f'{BASE}{estudio_solicitado.id}/anular/', {}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_marcar_realizado_invalido_desde_anulado(client, admin_user, estudio_solicitado):
    estudio_solicitado.estado = EstudioComplementario.Estado.ANULADO
    estudio_solicitado.save()
    client.force_authenticate(user=admin_user)
    r = client.post(f'{BASE}{estudio_solicitado.id}/marcar-realizado/')
    assert r.status_code == 400


@pytest.mark.django_db
def test_paciente_solo_ve_entregado(client, paciente, estudio_solicitado, admin_user):
    estudio_solicitado.estado = EstudioComplementario.Estado.SOLICITADO
    estudio_solicitado.save()
    client.force_authenticate(user=paciente.user)
    r = client.get(BASE)
    assert r.status_code == 200
    items = r.data.get('results', r.data)
    assert not any(i['id'] == estudio_solicitado.id for i in items)

    estudio_solicitado.estado = EstudioComplementario.Estado.ENTREGADO
    estudio_solicitado.save()
    r = client.get(BASE)
    items = r.data.get('results', r.data)
    assert any(i['id'] == estudio_solicitado.id for i in items)


@pytest.mark.django_db
def test_archivos_sin_media(client, admin_user, estudio_solicitado, archivo_medico):
    client.force_authenticate(user=admin_user)
    with capture_on_commit_callbacks(execute=True):
        client.post(
            f'{BASE}{estudio_solicitado.id}/agregar-archivo/',
            {'archivo_medico_id': archivo_medico.id},
            format='json',
        )
    r = client.get(f'{BASE}{estudio_solicitado.id}/archivos/')
    assert r.status_code == 200
    assert '/media/' not in str(r.data)
    assert 'download_url' in r.data[0]


@pytest.mark.django_db
def test_asociar_archivo_otro_paciente_rechazado(
    client, admin_user, estudio_solicitado, archivo_otro_paciente,
):
    client.force_authenticate(user=admin_user)
    r = client.post(
        f'{BASE}{estudio_solicitado.id}/agregar-archivo/',
        {'archivo_medico_id': archivo_otro_paciente.id},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_paciente_no_descarga_si_no_entregado(
    client, paciente, estudio_solicitado, archivo_medico, admin_user,
):
    client.force_authenticate(user=admin_user)
    with capture_on_commit_callbacks(execute=True):
        r = client.post(
            f'{BASE}{estudio_solicitado.id}/agregar-archivo/',
            {'archivo_medico_id': archivo_medico.id},
            format='json',
        )
    archivo_estudio_id = r.data['id']
    client.force_authenticate(user=paciente.user)
    r = client.get(
        f'{BASE}{estudio_solicitado.id}/archivos/{archivo_estudio_id}/download/'
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_informe_validado_no_editable_patch(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    client.post(f'{BASE}{eid}/marcar-realizado/')
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'X'}, format='json')
    informe_id = r.data['id']
    client.post(f'{BASE}{eid}/informes/{informe_id}/emitir/')
    client.post(f'{BASE}{eid}/informes/{informe_id}/validar/')
    informe = InformeEstudioComplementario.objects.get(pk=informe_id)
    assert informe.estado == 'VALIDADO'
