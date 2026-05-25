"""C6.4.3 — Hardening: único informe vigente (DB) y descarga protegida de PDF."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from auditoria.models import AuditEvent
from auditoria.snapshot import safe_model_snapshot
from auditoria.tests.compat import capture_on_commit_callbacks
from estudios.models import EstudioComplementario, InformeEstudioComplementario
from estudios.services import nombre_seguro_pdf_informe
from estudios.tests.test_informes_integridad import (
    BASE,
    _estudio_entregado_con_informe,
    _estudio_realizado,
)
from usuarios.models import User


def _adjuntar_pdf(informe, nombre_original='Juan_Perez_DNI123_informe.pdf'):
    informe.archivo_pdf.save(
        nombre_original,
        SimpleUploadedFile(nombre_original, b'%PDF-1.4 informe', content_type='application/pdf'),
        save=True,
    )


@pytest.mark.django_db
def test_no_pueden_existir_dos_informes_vigentes_por_constraint(estudio_solicitado):
    InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        es_vigente=True,
    )
    with pytest.raises(IntegrityError):
        InformeEstudioComplementario.objects.create(
            estudio=estudio_solicitado,
            version=2,
            estado=InformeEstudioComplementario.EstadoInforme.BORRADOR,
            es_vigente=True,
        )


@pytest.mark.django_db
def test_validar_informe_deja_unico_vigente_con_constraint(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        es_vigente=True,
    )
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'v2'}, format='json')
    iid = r.data['id']
    client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
    client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    vigentes = InformeEstudioComplementario.objects.filter(
        estudio_id=eid, es_vigente=True,
    )
    assert vigentes.count() == 1
    assert vigentes.first().pk == iid


@pytest.mark.django_db
def test_rectificacion_validada_respeta_constraint_unico_vigente(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'v1'}, format='json')
    iid = r.data['id']
    client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
    client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    client.post(f'{BASE}{eid}/entregar/')
    r = client.post(
        f'{BASE}{eid}/informes/{iid}/rectificar/',
        {'motivo_rectificacion': 'Corrección', 'texto': 'v2'},
        format='json',
    )
    nuevo_id = r.data['id']
    client.post(f'{BASE}{eid}/informes/{nuevo_id}/emitir/')
    client.post(f'{BASE}{eid}/informes/{nuevo_id}/validar/')
    assert (
        InformeEstudioComplementario.objects.filter(
            estudio_id=eid, es_vigente=True,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_admin_descarga_pdf_informe(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code == 200
    assert r['Content-Type'] == 'application/pdf'
    assert nombre_seguro_pdf_informe(eid, informe.version) in r['Content-Disposition']


@pytest.mark.django_db
def test_medico_vinculado_descarga_pdf_informe(
    client, medico, estudio_solicitado, admin_user, atencion_vinculada,
):
    estudio_solicitado.medico_solicitante = medico
    estudio_solicitado.atencion = atencion_vinculada
    estudio_solicitado.save()
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    client.force_authenticate(user=medico.user)
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_medico_ajeno_no_descarga_pdf_informe(
    client, medico_ajeno, estudio_solicitado, admin_user,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    client.force_authenticate(user=medico_ajeno.user)
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_paciente_descarga_pdf_solo_si_estudio_entregado_y_vigente(
    client, paciente, estudio_solicitado, admin_user,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    client.force_authenticate(user=paciente.user)
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_paciente_no_descarga_pdf_si_estudio_no_entregado(
    client, paciente, estudio_solicitado, admin_user,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'X'}, format='json')
    iid = r.data['id']
    client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
    client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    client.force_authenticate(user=paciente.user)
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_laboratorio_no_descarga_pdf_informe(
    client, estudio_solicitado, admin_user,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    lab = User.objects.create_user(username='lab_dl', password='x', rol='laboratorio')
    client.force_authenticate(user=lab)
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code == 403


@pytest.mark.django_db
def test_download_pdf_no_expone_media_ni_filename_original(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe, 'Paciente_Secreto_DNI999.pdf')
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code == 200
    disp = r['Content-Disposition']
    assert '/media/' not in disp
    assert 'Paciente_Secreto' not in disp
    assert 'DNI999' not in disp
    assert nombre_seguro_pdf_informe(eid, informe.version) in disp


@pytest.mark.django_db
def test_download_pdf_audita_evento_seguro(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    with capture_on_commit_callbacks(execute=True):
        client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    evs = [
        e for e in AuditEvent.objects.filter(module='estudios').order_by('-id')[:30]
        if (e.metadata or {}).get('accion') == 'estudio_informe_pdf_download'
    ]
    assert evs
    meta = evs[0].metadata or {}
    assert meta.get('estudio_id') == eid
    assert meta.get('informe_id') == iid
    assert '/media/' not in str(meta)
    assert 'Paciente' not in str(meta)
    after = evs[0].after_state or {}
    assert after.get('texto') is None or after.get('texto') != informe.texto


@pytest.mark.django_db
def test_download_pdf_404_si_informe_no_tiene_pdf(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    r = client.get(f'{BASE}{eid}/informes/{iid}/download-pdf/')
    assert r.status_code == 400


@pytest.mark.django_db
def test_download_pdf_rechaza_informe_de_otro_estudio(
    client, admin_user, estudio_solicitado, paciente, tipo_estudio,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    otro = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        estado=EstudioComplementario.Estado.SOLICITADO,
    )
    r = client.get(f'{BASE}{otro.id}/informes/{iid}/download-pdf/')
    assert r.status_code == 404


@pytest.mark.django_db
def test_informe_serializer_tiene_pdf_sin_media(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    iid = _estudio_entregado_con_informe(client, eid)
    informe = InformeEstudioComplementario.objects.get(pk=iid)
    _adjuntar_pdf(informe)
    r = client.get(f'{BASE}{eid}/informes/')
    assert r.status_code == 200
    row = next(x for x in r.data if x['id'] == iid)
    assert row['tiene_pdf'] is True
    assert '/media/' not in row['download_pdf_url']
    assert 'download-pdf' in row['download_pdf_url']


@pytest.mark.django_db
def test_snapshot_informe_no_incluye_archivo_pdf_path(estudio_solicitado, admin_user):
    informe = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        texto='Secreto clínico',
        creado_por=admin_user,
    )
    _adjuntar_pdf(informe, 'ruta_sensible.pdf')
    snap = safe_model_snapshot(informe)
    raw = str(snap)
    assert 'estudios/informes' not in raw
    assert 'ruta_sensible' not in raw
    assert snap.get('texto') != 'Secreto clínico'


@pytest.mark.django_db
def test_snapshot_informe_no_incluye_texto(estudio_solicitado):
    informe = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        texto='Texto PHI largo',
    )
    snap = safe_model_snapshot(informe)
    assert snap.get('texto') != 'Texto PHI largo'
