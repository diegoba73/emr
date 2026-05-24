"""Servicios de negocio — estudios complementarios (C6.4.1)."""

from __future__ import annotations

import logging
import os
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from archivos_medicos.models import ArchivoMedico
from auditoria.audit_service import log_event
from auditoria.snapshot import safe_model_snapshot

from .access import usuario_puede_validar_informe
from .estado import TransicionEstudioNoPermitida, aplicar_transicion_estudio
from .models import (
    ArchivoEstudioComplementario,
    EstudioComplementario,
    InformeEstudioComplementario,
)

logger = logging.getLogger(__name__)


def _safe_audit(callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
    except Exception:  # pragma: no cover
        logger.exception('Fallo silencioso en auditoría: %s', getattr(callable_, '__name__', 'audit'))


def _estudio_meta(estudio: EstudioComplementario, **extra: Any) -> dict:
    return {'estudio_id': estudio.pk, **extra}


def _informe_snapshot(informe: InformeEstudioComplementario) -> dict:
    snap = safe_model_snapshot(informe)
    snap.pop('texto', None)
    return snap


def _siguiente_version_informe(estudio_id: int) -> int:
    last = (
        InformeEstudioComplementario.objects.filter(estudio_id=estudio_id)
        .order_by('-version')
        .values_list('version', flat=True)
        .first()
    )
    return (last or 0) + 1


@transaction.atomic
def crear_estudio(validated_data: dict, *, user) -> EstudioComplementario:
    estudio = EstudioComplementario(**validated_data)
    estudio.creado_por = user
    estudio.modificado_por = user
    if not estudio.fecha_solicitud:
        estudio.fecha_solicitud = timezone.now()
    estudio.full_clean()
    estudio.save()
    _safe_audit(
        log_event,
        action='CREATE',
        actor=user,
        entity=estudio,
        after=safe_model_snapshot(estudio),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_complementario_create',
            'view': 'EstudioComplementarioViewSet',
            **_estudio_meta(estudio, estado=estudio.estado),
        },
    )
    return estudio


@transaction.atomic
def actualizar_estudio(estudio: EstudioComplementario, validated_data: dict, *, user) -> EstudioComplementario:
    if estudio.es_terminal:
        raise ValidationError('El estudio no admite modificaciones en su estado actual.')
    before = safe_model_snapshot(estudio)
    for key, value in validated_data.items():
        setattr(estudio, key, value)
    estudio.modificado_por = user
    estudio.full_clean()
    estudio.save()
    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=estudio,
        before=before,
        after=safe_model_snapshot(estudio),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_complementario_update',
            'view': 'EstudioComplementarioViewSet',
            **_estudio_meta(estudio, estado=estudio.estado),
        },
    )
    return estudio


def _auditar_cambio_estado(
    estudio: EstudioComplementario,
    *,
    user,
    accion: str,
    estado_anterior: str,
    estado_nuevo: str,
):
    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=estudio,
        after=safe_model_snapshot(estudio),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        module='estudios',
        metadata={
            'accion': accion,
            'view': 'EstudioComplementarioViewSet',
            'estado_anterior': estado_anterior,
            'estado_nuevo': estado_nuevo,
            **_estudio_meta(estudio),
        },
    )


@transaction.atomic
def marcar_realizado(estudio: EstudioComplementario, *, user, fecha_realizacion=None):
    estudio.fecha_realizacion = fecha_realizacion or timezone.now()
    estudio.modificado_por = user
    estudio.full_clean()
    anterior = aplicar_transicion_estudio(
        estudio,
        accion='marcar_realizado',
        nuevo_estado=EstudioComplementario.Estado.REALIZADO,
    )
    estudio.save(update_fields=['fecha_realizacion', 'modificado_por', 'updated_at'])
    _auditar_cambio_estado(
        estudio,
        user=user,
        accion='estudio_estado_cambio',
        estado_anterior=anterior,
        estado_nuevo=estudio.estado,
    )
    return estudio


@transaction.atomic
def anular_estudio(estudio: EstudioComplementario, *, user, motivo: str):
    if not motivo or not str(motivo).strip():
        raise ValidationError({'motivo_anulacion': 'El motivo de anulación es obligatorio.'})
    estudio.motivo_anulacion = motivo.strip()
    estudio.modificado_por = user
    anterior = aplicar_transicion_estudio(
        estudio,
        accion='anular',
        nuevo_estado=EstudioComplementario.Estado.ANULADO,
    )
    estudio.save(update_fields=['motivo_anulacion', 'modificado_por', 'updated_at'])
    _auditar_cambio_estado(
        estudio,
        user=user,
        accion='estudio_anular',
        estado_anterior=anterior,
        estado_nuevo=estudio.estado,
    )
    return estudio


def _informe_vigente_validado(estudio: EstudioComplementario) -> InformeEstudioComplementario | None:
    return (
        InformeEstudioComplementario.objects.filter(
            estudio=estudio,
            es_vigente=True,
            estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        )
        .order_by('-version')
        .first()
    )


@transaction.atomic
def entregar_estudio(estudio: EstudioComplementario, *, user):
    if not _informe_vigente_validado(estudio):
        raise ValidationError('Entregar requiere un informe validado vigente.')
    if estudio.estado != EstudioComplementario.Estado.VALIDADO:
        raise ValidationError('El estudio debe estar en estado VALIDADO para entregar.')
    anterior = aplicar_transicion_estudio(
        estudio,
        accion='entregar',
        nuevo_estado=EstudioComplementario.Estado.ENTREGADO,
    )
    estudio.modificado_por = user
    estudio.save(update_fields=['modificado_por', 'updated_at'])
    _auditar_cambio_estado(
        estudio,
        user=user,
        accion='estudio_entregar',
        estado_anterior=anterior,
        estado_nuevo=estudio.estado,
    )
    return estudio


@transaction.atomic
def asociar_archivo(
    estudio: EstudioComplementario,
    *,
    user,
    archivo_medico_id: int,
    tipo_rol: str = ArchivoEstudioComplementario.TipoRol.OTRO,
    descripcion: str = '',
    orden: int = 0,
    es_principal: bool = False,
) -> ArchivoEstudioComplementario:
    if estudio.es_terminal:
        raise ValidationError('No se pueden asociar archivos a un estudio terminal.')
    try:
        archivo_medico = ArchivoMedico.objects.get(pk=archivo_medico_id)
    except ArchivoMedico.DoesNotExist as exc:
        raise ValidationError({'archivo_medico_id': 'Archivo médico no encontrado.'}) from exc

    vinculo = ArchivoEstudioComplementario(
        estudio=estudio,
        archivo_medico=archivo_medico,
        tipo_rol=tipo_rol,
        descripcion=descripcion or '',
        orden=orden,
        es_principal=es_principal,
        subido_por=user,
    )
    vinculo.full_clean()
    vinculo.save()
    _safe_audit(
        log_event,
        action='CREATE',
        actor=user,
        entity=vinculo,
        after=safe_model_snapshot(vinculo),
        entity_repr=f'estudios.ArchivoEstudioComplementario:{vinculo.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_archivo_asociar',
            'view': 'EstudioComplementarioViewSet.agregar_archivo',
            'archivo_estudio_id': vinculo.pk,
            'archivo_medico_id': archivo_medico.pk,
            **_estudio_meta(estudio),
        },
    )
    return vinculo


def servir_descarga_archivo_estudio(vinculo: ArchivoEstudioComplementario, *, user):
    archivo = vinculo.archivo_medico
    if not archivo.archivo:
        raise ValidationError('Archivo no encontrado en el servidor.')

    try:
        storage_path = archivo.archivo.path
    except Exception as exc:
        raise ValidationError('Archivo no encontrado en el servidor.') from exc

    if not os.path.exists(storage_path):
        logger.error('Archivo clínico ausente en almacenamiento (estudio)')
        raise ValidationError('Archivo no encontrado en el servidor.')

    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=vinculo,
        after=safe_model_snapshot(vinculo),
        entity_repr=f'estudios.ArchivoEstudioComplementario:{vinculo.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_archivo_download',
            'view': 'EstudioComplementarioViewSet.download_archivo',
            'archivo_estudio_id': vinculo.pk,
            'archivo_medico_id': archivo.pk,
            **_estudio_meta(vinculo.estudio),
        },
    )

    response = FileResponse(open(storage_path, 'rb'), content_type='application/octet-stream')
    nombre_descarga = os.path.basename(archivo.archivo.name) or 'archivo'
    nombre_descarga = nombre_descarga.replace('"', '_')
    response['Content-Disposition'] = f'attachment; filename="{nombre_descarga}"'
    return response


@transaction.atomic
def crear_informe(
    estudio: EstudioComplementario,
    *,
    user,
    texto: str = '',
    tipo: str = InformeEstudioComplementario.TipoInforme.FINAL,
) -> InformeEstudioComplementario:
    if estudio.es_terminal:
        raise ValidationError('No se pueden crear informes en un estudio terminal.')
    informe = InformeEstudioComplementario(
        estudio=estudio,
        version=_siguiente_version_informe(estudio.pk),
        texto=texto or '',
        tipo=tipo,
        creado_por=user,
        es_vigente=True,
    )
    InformeEstudioComplementario.objects.filter(estudio=estudio, es_vigente=True).update(
        es_vigente=False
    )
    informe.save()
    _safe_audit(
        log_event,
        action='CREATE',
        actor=user,
        entity=informe,
        after=_informe_snapshot(informe),
        entity_repr=f'estudios.InformeEstudioComplementario:{informe.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_informe_create',
            'view': 'EstudioComplementarioViewSet.informes',
            'informe_id': informe.pk,
            'version_informe': informe.version,
            **_estudio_meta(estudio),
        },
    )
    return informe


@transaction.atomic
def emitir_informe(informe: InformeEstudioComplementario, *, user, medico=None):
    if informe.estado != InformeEstudioComplementario.EstadoInforme.BORRADOR:
        raise ValidationError('Solo se puede emitir un informe en borrador.')
    if informe.estudio.es_terminal:
        raise ValidationError('El estudio no admite informes en su estado actual.')
    informe.estado = InformeEstudioComplementario.EstadoInforme.EMITIDO
    informe.fecha_informe = timezone.now()
    if medico:
        informe.informado_por = medico
    informe.save()
    estudio = informe.estudio
    if estudio.estado == EstudioComplementario.Estado.REALIZADO:
        anterior = aplicar_transicion_estudio(
            estudio,
            accion='informar',
            nuevo_estado=EstudioComplementario.Estado.INFORMADO,
        )
        _auditar_cambio_estado(
            estudio,
            user=user,
            accion='estudio_estado_cambio',
            estado_anterior=anterior,
            estado_nuevo=estudio.estado,
        )
    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=informe,
        after=_informe_snapshot(informe),
        entity_repr=f'estudios.InformeEstudioComplementario:{informe.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_informe_emitir',
            'view': 'EstudioComplementarioViewSet.emitir_informe',
            'informe_id': informe.pk,
            'version_informe': informe.version,
            **_estudio_meta(estudio),
        },
    )
    return informe


@transaction.atomic
def validar_informe(informe: InformeEstudioComplementario, *, user):
    if not usuario_puede_validar_informe(user):
        raise PermissionDenied('No tiene permiso para validar informes.')
    if informe.estado != InformeEstudioComplementario.EstadoInforme.EMITIDO:
        raise ValidationError('Solo se puede validar un informe emitido.')
    informe.estado = InformeEstudioComplementario.EstadoInforme.VALIDADO
    informe.validado_por = user
    informe.fecha_validacion = timezone.now()
    informe.es_vigente = True
    informe.save()
    estudio = informe.estudio
    if estudio.estado == EstudioComplementario.Estado.INFORMADO:
        anterior = aplicar_transicion_estudio(
            estudio,
            accion='validar',
            nuevo_estado=EstudioComplementario.Estado.VALIDADO,
        )
        _auditar_cambio_estado(
            estudio,
            user=user,
            accion='estudio_estado_cambio',
            estado_anterior=anterior,
            estado_nuevo=estudio.estado,
        )
    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=informe,
        after=_informe_snapshot(informe),
        entity_repr=f'estudios.InformeEstudioComplementario:{informe.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_informe_validar',
            'view': 'EstudioComplementarioViewSet.validar_informe',
            'informe_id': informe.pk,
            'version_informe': informe.version,
            **_estudio_meta(estudio),
        },
    )
    return informe


@transaction.atomic
def rectificar_informe(
    informe: InformeEstudioComplementario,
    *,
    user,
    motivo: str,
    texto: str = '',
):
    if informe.estado != InformeEstudioComplementario.EstadoInforme.VALIDADO:
        raise ValidationError('Solo se puede rectificar un informe validado.')
    if not motivo or not str(motivo).strip():
        raise ValidationError({'motivo_rectificacion': 'El motivo de rectificación es obligatorio.'})
    estudio = informe.estudio
    if estudio.es_terminal:
        raise ValidationError('El estudio no admite rectificación en su estado actual.')

    informe.es_vigente = False
    informe.save(update_fields=['es_vigente', 'updated_at'])

    nuevo = InformeEstudioComplementario(
        estudio=estudio,
        version=_siguiente_version_informe(estudio.pk),
        estado=InformeEstudioComplementario.EstadoInforme.BORRADOR,
        tipo=informe.tipo,
        texto=texto or '',
        es_vigente=True,
        reemplaza_a=informe,
        motivo_rectificacion=motivo.strip(),
        creado_por=user,
    )
    nuevo.save()

    if estudio.estado == EstudioComplementario.Estado.VALIDADO:
        try:
            anterior = aplicar_transicion_estudio(
                estudio,
                accion='rectificar',
                nuevo_estado=EstudioComplementario.Estado.INFORMADO,
            )
            _auditar_cambio_estado(
                estudio,
                user=user,
                accion='estudio_estado_cambio',
                estado_anterior=anterior,
                estado_nuevo=estudio.estado,
            )
        except TransicionEstudioNoPermitida:
            pass

    _safe_audit(
        log_event,
        action='CREATE',
        actor=user,
        entity=nuevo,
        after=_informe_snapshot(nuevo),
        entity_repr=f'estudios.InformeEstudioComplementario:{nuevo.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_informe_rectificar',
            'view': 'EstudioComplementarioViewSet.rectificar_informe',
            'informe_id': nuevo.pk,
            'version_informe': nuevo.version,
            'informe_reemplazado_id': informe.pk,
            **_estudio_meta(estudio),
        },
    )
    return nuevo
