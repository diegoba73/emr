"""A2/A2b — tipo_actividad, snapshot, PATCH protegido, altas off, A2b, PROTECT.

Usa fixtures ORM para proc/cirugía (altas públicas deshabilitadas).
No toca laboratorio/.
"""
from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from catalogos.models import ProcedimientoCatalogo
from estudios.models import EstudioComplementario
from estudios.actividad_rules import validar_correspondencia_actividad
from estudios.services import (
    corregir_clasificacion_snapshot,
    marcar_realizado,
)
BASE = '/api/estudios-complementarios/'


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


@pytest.fixture
def proc_no_quir(db):
    return ProcedimientoCatalogo.objects.create(
        nombre=f'Proc NQ {_uid()}',
        activo=True,
        clasificacion_quirurgica=ProcedimientoCatalogo.ClasificacionQuirurgica.NO_QUIRURGICO,
    )


@pytest.fixture
def proc_quir(db):
    return ProcedimientoCatalogo.objects.create(
        nombre=f'Proc Q {_uid()}',
        activo=True,
        clasificacion_quirurgica=ProcedimientoCatalogo.ClasificacionQuirurgica.QUIRURGICO,
    )


def _force_proc_estudio(paciente, proc, *, tipo='PROCEDIMIENTO', snap='NO_QUIRURGICO', estado='SOLICITADO'):
    """Alta no pública: fila controlada en DB para probar reglas."""
    e = EstudioComplementario(
        paciente=paciente,
        practica='IMAGEN_RX',
        tipo_actividad=tipo,
        procedimiento_catalogo=proc,
        clasificacion_quirurgica_snapshot=snap,
        permite_multi_sesion=False,
        estado=estado,
    )
    # save sin full_clean para armar escenarios; clean se prueba aparte.
    e.save()
    return e


@pytest.mark.django_db
def test_matriz_correspondencia_contradictoria(proc_no_quir, proc_quir):
    with pytest.raises(DjangoValidationError):
        validar_correspondencia_actividad(
            tipo_actividad='ESTUDIO',
            procedimiento_catalogo=proc_no_quir,
            clasificacion_quirurgica_snapshot='',
        )
    with pytest.raises(DjangoValidationError):
        validar_correspondencia_actividad(
            tipo_actividad='PROCEDIMIENTO',
            procedimiento_catalogo=proc_quir,
            clasificacion_quirurgica_snapshot='NO_QUIRURGICO',
        )
    with pytest.raises(DjangoValidationError):
        validar_correspondencia_actividad(
            tipo_actividad='CIRUGIA',
            procedimiento_catalogo=proc_quir,
            clasificacion_quirurgica_snapshot='NO_QUIRURGICO',
        )
    with pytest.raises(DjangoValidationError):
        validar_correspondencia_actividad(
            tipo_actividad='ESTUDIO',
            permite_multi_sesion=True,
        )
    # Válidos
    validar_correspondencia_actividad(tipo_actividad='ESTUDIO')
    validar_correspondencia_actividad(
        tipo_actividad='PROCEDIMIENTO',
        procedimiento_catalogo=proc_no_quir,
        clasificacion_quirurgica_snapshot='NO_QUIRURGICO',
    )
    validar_correspondencia_actividad(
        tipo_actividad='CIRUGIA',
        procedimiento_catalogo=proc_quir,
        clasificacion_quirurgica_snapshot='QUIRURGICO',
    )


@pytest.mark.django_db
def test_create_legacy_estudio_ok(admin_client, paciente, tipo_estudio, medico):
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.pk,
            'tipo_estudio': tipo_estudio.pk,
            'practica': tipo_estudio.practica,
            'medico_solicitante': medico.pk,
        },
        format='json',
    )
    assert r.status_code == status.HTTP_201_CREATED, r.data
    assert r.data['tipo_actividad'] == 'ESTUDIO'
    assert r.data.get('procedimiento_catalogo') in (None, '')
    assert not r.data.get('clasificacion_quirurgica_snapshot')
    assert r.data.get('permite_multi_sesion') is False
    assert r.data['medico_solicitante'] == medico.pk


@pytest.mark.django_db
def test_create_cirugia_exige_catalogo_jerarquico(admin_client, paciente, tipo_estudio, medico):
    """CIRUGIA habilitada; sin especialidad/procedimiento jerárquico → 400."""
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.pk,
            'tipo_estudio': tipo_estudio.pk,
            'practica': tipo_estudio.practica,
            'tipo_actividad': 'CIRUGIA',
            'medico_solicitante': medico.pk,
        },
        format='json',
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert 'cirugia_especialidad' in r.data or 'cirugia_procedimiento' in r.data


@pytest.mark.django_db
def test_patch_campos_protegidos(admin_client, paciente, tipo_estudio, proc_no_quir, medico):
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.pk,
            'tipo_estudio': tipo_estudio.pk,
            'practica': tipo_estudio.practica,
            'medico_solicitante': medico.pk,
        },
        format='json',
    )
    assert r.status_code == 201
    pk = r.data['id']
    for payload in (
        {'tipo_actividad': 'PROCEDIMIENTO'},
        {'procedimiento_catalogo': proc_no_quir.pk},
        {'clasificacion_quirurgica_snapshot': 'NO_QUIRURGICO'},
        {'permite_multi_sesion': True},
    ):
        rp = admin_client.patch(f'{BASE}{pk}/', payload, format='json')
        assert rp.status_code == status.HTTP_400_BAD_REQUEST, payload
    # Sin cambio en DB
    e = EstudioComplementario.objects.get(pk=pk)
    assert e.tipo_actividad == 'ESTUDIO'
    assert e.procedimiento_catalogo_id is None
    assert e.permite_multi_sesion is False


@pytest.mark.django_db
def test_marcar_realizado_bloquea_no_estudio(paciente, proc_no_quir, admin_user):
    e = _force_proc_estudio(paciente, proc_no_quir)
    with pytest.raises(DjangoValidationError):
        marcar_realizado(e, user=admin_user)


@pytest.mark.django_db
def test_a2b_admin_ok_y_audit(paciente, proc_no_quir, admin_user):
    e = _force_proc_estudio(paciente, proc_no_quir, snap='NO_QUIRURGICO')
    # Corrección “compatible” (mismo valor permitido) con motivo.
    out = corregir_clasificacion_snapshot(
        e,
        clasificacion_quirurgica_snapshot='NO_QUIRURGICO',
        motivo='Ajuste documental de prueba',
        user=admin_user,
    )
    assert out.clasificacion_quirurgica_snapshot == 'NO_QUIRURGICO'
    found = AuditEvent.objects.filter(entity_id=str(e.pk)).order_by('-id')
    assert found.exists()
    meta = found.first().metadata or {}
    assert meta.get('accion') == 'estudio_clasificacion_correccion'
    assert 'motivo' in meta


@pytest.mark.django_db
def test_a2b_incompatible_y_post_realizacion(paciente, proc_no_quir, proc_quir, admin_user):
    e = _force_proc_estudio(paciente, proc_no_quir)
    with pytest.raises(DjangoValidationError):
        corregir_clasificacion_snapshot(
            e,
            clasificacion_quirurgica_snapshot='QUIRURGICO',
            motivo='intento incompatible',
            user=admin_user,
        )
    e2 = _force_proc_estudio(
        paciente, proc_no_quir, estado=EstudioComplementario.Estado.REALIZADO
    )
    with pytest.raises(DjangoValidationError):
        corregir_clasificacion_snapshot(
            e2,
            clasificacion_quirurgica_snapshot='NO_QUIRURGICO',
            motivo='post realizado',
            user=admin_user,
        )


@pytest.mark.django_db
def test_a2b_no_admin_403(paciente, proc_no_quir, medico):
    e = _force_proc_estudio(paciente, proc_no_quir)
    client = APIClient()
    client.force_authenticate(medico.user)
    r = client.post(
        f'{BASE}{e.pk}/corregir-clasificacion-snapshot/',
        {'clasificacion_quirurgica_snapshot': 'NO_QUIRURGICO', 'motivo': 'x'},
        format='json',
    )
    assert r.status_code in (
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.django_db
def test_a2b_api_admin(admin_client, paciente, proc_no_quir):
    e = _force_proc_estudio(paciente, proc_no_quir)
    r = admin_client.post(
        f'{BASE}{e.pk}/corregir-clasificacion-snapshot/',
        {
            'clasificacion_quirurgica_snapshot': 'NO_QUIRURGICO',
            'motivo': 'Corrección admin A2b',
        },
        format='json',
    )
    assert r.status_code == status.HTTP_200_OK, r.data
    assert r.data['clasificacion_quirurgica_snapshot'] == 'NO_QUIRURGICO'


@pytest.mark.django_db
def test_protect_delete_catalogo_referenciado(paciente, proc_no_quir):
    _force_proc_estudio(paciente, proc_no_quir)
    with pytest.raises(IntegrityError):
        proc_no_quir.delete()
    proc_no_quir.activo = False
    proc_no_quir.save(update_fields=['activo'])
    proc_no_quir.refresh_from_db()
    assert proc_no_quir.activo is False


@pytest.mark.django_db
def test_backfill_idempotente_no_pisa_proc(
    paciente, otro_paciente, tipo_estudio, proc_no_quir, admin_user,
):
    """Conserva conteos/relaciones legacy; reejecutar backfill no pisa PROCEDIMIENTO."""
    import importlib

    leg = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        origen=EstudioComplementario.Origen.INTERNO,
        descripcion_clinica='legacy-a2',
        creado_por=admin_user,
    )
    snap_leg = {
        'id': leg.pk,
        'paciente_id': leg.paciente_id,
        'tipo_estudio_id': leg.tipo_estudio_id,
        'practica': leg.practica,
        'origen': leg.origen,
        'descripcion_clinica': leg.descripcion_clinica,
        'creado_por_id': leg.creado_por_id,
        'estado': leg.estado,
    }
    proc_row = _force_proc_estudio(paciente, proc_no_quir)
    count_before = EstudioComplementario.objects.count()

    mig = importlib.import_module(
        'estudios.migrations.0006_estudio_tipo_actividad_a2'
    )

    class FakeApps:
        @staticmethod
        def get_model(app, model):
            from django.apps import apps
            return apps.get_model(app, model)

    mig.backfill_tipo_actividad_estudio(FakeApps, None)
    mig.backfill_tipo_actividad_estudio(FakeApps, None)  # reejecución

    assert EstudioComplementario.objects.count() == count_before
    leg.refresh_from_db()
    proc_row.refresh_from_db()
    assert leg.paciente_id == snap_leg['paciente_id']
    assert leg.tipo_estudio_id == snap_leg['tipo_estudio_id']
    assert leg.practica == snap_leg['practica']
    assert leg.origen == snap_leg['origen']
    assert leg.descripcion_clinica == snap_leg['descripcion_clinica']
    assert leg.creado_por_id == snap_leg['creado_por_id']
    assert leg.estado == snap_leg['estado']
    assert leg.tipo_actividad == 'ESTUDIO'
    assert leg.procedimiento_catalogo_id is None
    assert proc_row.tipo_actividad == 'PROCEDIMIENTO'
    assert proc_row.procedimiento_catalogo_id == proc_no_quir.pk
    assert proc_row.clasificacion_quirurgica_snapshot == 'NO_QUIRURGICO'


@pytest.mark.django_db
def test_a2b_rollback_si_falla_auditoria(paciente, proc_no_quir, admin_user, monkeypatch):
    """Si AuditEvent.create falla, la TX revierte el snapshot (sin cambio parcial)."""
    e = _force_proc_estudio(paciente, proc_no_quir, snap=None)
    assert e.clasificacion_quirurgica_snapshot in (None, '')

    def _boom(**kwargs):
        raise RuntimeError('audit-fail-a2b')

    monkeypatch.setattr(
        'estudios.services.AuditEvent.objects.create',
        _boom,
    )
    with pytest.raises(RuntimeError, match='audit-fail-a2b'):
        corregir_clasificacion_snapshot(
            e,
            clasificacion_quirurgica_snapshot='NO_QUIRURGICO',
            motivo='debe revertir',
            user=admin_user,
        )
    e.refresh_from_db()
    assert e.clasificacion_quirurgica_snapshot in (None, '')
    assert not AuditEvent.objects.filter(
        entity_id=str(e.pk),
        metadata__accion='estudio_clasificacion_correccion',
    ).exists()
