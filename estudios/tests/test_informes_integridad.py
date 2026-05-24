"""C6.4.1-A — Integridad de informes y PATCH de paciente."""

from __future__ import annotations

import pytest

from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from estudios.models import EstudioComplementario, InformeEstudioComplementario
from estudios.tests.conftest import _payload_crear

BASE = '/api/estudios-complementarios/'


def _estudio_realizado(client, estudio_id):
    return client.post(f'{BASE}{estudio_id}/marcar-realizado/')


@pytest.mark.django_db
def test_medico_no_puede_patch_paciente_id_a_paciente_ajeno(
    client, medico, paciente, otro_paciente, tipo_estudio, atencion_vinculada,
):
    client.force_authenticate(user=medico.user)
    r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    assert r.status_code == 201
    eid = r.data['id']
    r = client.patch(
        f'{BASE}{eid}/',
        {'paciente_id': otro_paciente.id},
        format='json',
    )
    assert r.status_code == 400
    estudio = EstudioComplementario.objects.get(pk=eid)
    assert estudio.paciente_id == paciente.id


@pytest.mark.django_db
def test_admin_no_puede_patch_paciente_id_por_patch_comun(
    client, admin_user, paciente, otro_paciente, tipo_estudio, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    r = client.patch(
        f'{BASE}{estudio_solicitado.id}/',
        {'paciente_id': otro_paciente.id},
        format='json',
    )
    assert r.status_code == 400
    estudio_solicitado.refresh_from_db()
    assert estudio_solicitado.paciente_id == paciente.id


@pytest.mark.django_db
def test_no_puede_crear_informe_en_solicitado(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    r = client.post(
        f'{BASE}{estudio_solicitado.id}/informes/',
        {'texto': 'X'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_puede_crear_informe_en_realizado(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    _estudio_realizado(client, estudio_solicitado.id)
    r = client.post(
        f'{BASE}{estudio_solicitado.id}/informes/',
        {'texto': 'Hallazgos'},
        format='json',
    )
    assert r.status_code == 201
    assert r.data['estado'] == 'BORRADOR'
    assert r.data['es_vigente'] is False


@pytest.mark.django_db
def test_no_puede_emitir_informe_en_estudio_solicitado(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    estudio_solicitado.estado = EstudioComplementario.Estado.SOLICITADO
    estudio_solicitado.save()
    informe = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        texto='X',
        estado=InformeEstudioComplementario.EstadoInforme.BORRADOR,
    )
    r = client.post(
        f'{BASE}{estudio_solicitado.id}/informes/{informe.id}/emitir/',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_emitir_informe_en_realizado_pasa_estudio_a_informado(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'X'}, format='json')
    informe_id = r.data['id']
    r = client.post(f'{BASE}{eid}/informes/{informe_id}/emitir/')
    assert r.status_code == 200
    estudio_solicitado.refresh_from_db()
    assert estudio_solicitado.estado == EstudioComplementario.Estado.INFORMADO


@pytest.mark.django_db
def test_no_puede_validar_informe_si_estudio_no_esta_informado(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'X'}, format='json')
    informe_id = r.data['id']
    informe = InformeEstudioComplementario.objects.get(pk=informe_id)
    informe.estado = InformeEstudioComplementario.EstadoInforme.EMITIDO
    informe.save()
    estudio_solicitado.refresh_from_db()
    assert estudio_solicitado.estado == EstudioComplementario.Estado.REALIZADO
    r = client.post(f'{BASE}{eid}/informes/{informe_id}/validar/')
    assert r.status_code == 400


@pytest.mark.django_db
def test_validar_informe_desactiva_otros_vigentes(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    i1 = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        texto='v1',
        estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        es_vigente=True,
    )
    estudio_solicitado.estado = EstudioComplementario.Estado.INFORMADO
    estudio_solicitado.save()
    i2 = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=2,
        texto='v2',
        estado=InformeEstudioComplementario.EstadoInforme.EMITIDO,
        es_vigente=False,
    )
    client.post(f'{BASE}{eid}/informes/{i2.id}/validar/')
    i1.refresh_from_db()
    i2.refresh_from_db()
    assert i1.es_vigente is False
    assert i2.es_vigente is True
    assert i2.estado == InformeEstudioComplementario.EstadoInforme.VALIDADO


@pytest.mark.django_db
def test_no_quedan_dos_informes_vigentes_por_flujo_normal(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    with capture_on_commit_callbacks(execute=True):
        _estudio_realizado(client, eid)
        r = client.post(f'{BASE}{eid}/informes/', {'texto': 'A'}, format='json')
        iid = r.data['id']
        client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
        client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    vigentes = InformeEstudioComplementario.objects.filter(
        estudio_id=eid, es_vigente=True,
    )
    assert vigentes.count() == 1


@pytest.mark.django_db
def test_medico_no_puede_validar_informe(
    client, medico, paciente, tipo_estudio, atencion_vinculada,
):
    client.force_authenticate(user=medico.user)
    r = client.post(BASE, _payload_crear(paciente, tipo_estudio), format='json')
    eid = r.data['id']
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'X'}, format='json')
    iid = r.data['id']
    client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
    r = client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    assert r.status_code == 403


@pytest.mark.django_db
def test_rectificar_crea_nueva_version_no_vigente(client, admin_user, estudio_solicitado):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'v1'}, format='json')
    iid = r.data['id']
    client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
    client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    viejo = InformeEstudioComplementario.objects.get(pk=iid)
    assert viejo.es_vigente is True
    r = client.post(
        f'{BASE}{eid}/informes/{iid}/rectificar/',
        {'motivo_rectificacion': 'Error menor', 'texto': 'v2'},
        format='json',
    )
    assert r.status_code == 201
    nuevo = InformeEstudioComplementario.objects.get(pk=r.data['id'])
    viejo.refresh_from_db()
    assert nuevo.es_vigente is False
    assert viejo.es_vigente is True
    assert nuevo.reemplaza_a_id == viejo.id


@pytest.mark.django_db
def test_validar_rectificacion_deja_solo_nueva_version_vigente(
    client, admin_user, estudio_solicitado,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    _estudio_realizado(client, eid)
    r = client.post(f'{BASE}{eid}/informes/', {'texto': 'v1'}, format='json')
    iid = r.data['id']
    client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
    client.post(f'{BASE}{eid}/informes/{iid}/validar/')
    r = client.post(
        f'{BASE}{eid}/informes/{iid}/rectificar/',
        {'motivo_rectificacion': 'Corrección', 'texto': 'v2'},
        format='json',
    )
    nuevo_id = r.data['id']
    client.post(f'{BASE}{eid}/informes/{nuevo_id}/emitir/')
    client.post(f'{BASE}{eid}/informes/{nuevo_id}/validar/')
    vigentes = InformeEstudioComplementario.objects.filter(
        estudio_id=eid, es_vigente=True, estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
    )
    assert vigentes.count() == 1
    assert vigentes.first().pk == nuevo_id


@pytest.mark.django_db
def test_enfermeria_no_accede_estudios(client, db, estudio_solicitado):
    from usuarios.models import User

    u = User.objects.create_user(username='enf_c641a', password='x', rol='enfermeria')
    client.force_authenticate(user=u)
    r = client.get(f'{BASE}{estudio_solicitado.id}/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_download_archivo_genera_auditoria(
    client, admin_user, estudio_solicitado, archivo_medico,
):
    client.force_authenticate(user=admin_user)
    with capture_on_commit_callbacks(execute=True):
        r = client.post(
            f'{BASE}{estudio_solicitado.id}/agregar-archivo/',
            {'archivo_medico_id': archivo_medico.id},
            format='json',
        )
        archivo_estudio_id = r.data['id']
        client.get(
            f'{BASE}{estudio_solicitado.id}/archivos/{archivo_estudio_id}/download/'
        )
    evs = [
        e for e in AuditEvent.objects.filter(module='estudios').order_by('-id')[:30]
        if (e.metadata or {}).get('accion') == 'estudio_archivo_download'
    ]
    assert len(evs) >= 1


@pytest.mark.django_db
def test_paciente_descarga_archivo_entregado(
    client, paciente, estudio_solicitado, archivo_medico, admin_user,
):
    client.force_authenticate(user=admin_user)
    eid = estudio_solicitado.id
    with capture_on_commit_callbacks(execute=True):
        _estudio_realizado(client, eid)
        r = client.post(
            f'{BASE}{eid}/agregar-archivo/',
            {'archivo_medico_id': archivo_medico.id},
            format='json',
        )
        archivo_estudio_id = r.data['id']
        r = client.post(f'{BASE}{eid}/informes/', {'texto': 'X'}, format='json')
        iid = r.data['id']
        client.post(f'{BASE}{eid}/informes/{iid}/emitir/')
        client.post(f'{BASE}{eid}/informes/{iid}/validar/')
        client.post(f'{BASE}{eid}/entregar/')
    client.force_authenticate(user=paciente.user)
    r = client.get(f'{BASE}{eid}/archivos/{archivo_estudio_id}/download/')
    assert r.status_code == 200
