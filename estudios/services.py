"""Servicios de negocio — estudios complementarios (C6.4.1)."""

from __future__ import annotations

import logging
import os
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from archivos_medicos.models import ArchivoMedico
from auditoria.audit_service import log_event
from auditoria.snapshot import safe_model_snapshot

from .access import usuario_puede_descargar_pdf_informe, usuario_puede_validar_informe
from .estado import aplicar_transicion_estudio
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


_ESTADOS_CREAR_EMITIR_INFORME = frozenset({
    EstudioComplementario.Estado.REALIZADO,
    EstudioComplementario.Estado.INFORMADO,
})


def _exigir_estado_estudio(
    estudio: EstudioComplementario,
    estados_permitidos: frozenset,
    mensaje: str,
) -> None:
    if estudio.estado not in estados_permitidos:
        raise ValidationError(mensaje)


def nombre_seguro_pdf_informe(estudio_id: int, version: int) -> str:
    return f'estudio-complementario-{estudio_id}-informe-v{version}.pdf'


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


_TIPOS_RECURSO_ESTUDIO = frozenset({'SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'})


def _motivo_turno_desde_estudio(estudio: EstudioComplementario) -> str:
    nombre = ''
    if estudio.tipo_estudio_id and estudio.tipo_estudio:
        nombre = estudio.tipo_estudio.nombre
    if not nombre:
        nombre = estudio.get_modalidad_display()
    return f'Estudio: {nombre}'[:255]


@transaction.atomic
def asignar_turno_estudio(
    estudio: EstudioComplementario,
    *,
    user,
    recurso,
    fecha_hora_inicio,
    fecha_hora_fin,
    medico=None,
):
    from turnos.models import Turno

    if estudio.estado != EstudioComplementario.Estado.SOLICITADO:
        raise ValidationError('Solo se puede asignar turno a estudios en estado Solicitado.')
    if estudio.turno_id:
        raise ValidationError('El estudio ya tiene un turno asignado.')
    if recurso.tipo_recurso not in _TIPOS_RECURSO_ESTUDIO:
        raise ValidationError(
            {'recurso_id': 'El recurso debe ser sala de procedimiento o hemodinamia.'}
        )
    if fecha_hora_fin and fecha_hora_fin <= fecha_hora_inicio:
        raise ValidationError(
            {'fecha_hora_fin': 'La fecha/hora de fin debe ser posterior al inicio.'}
        )

    from turnos.validacion_sala import validar_disponibilidad_sala_estudio

    validar_disponibilidad_sala_estudio(
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
    )

    turno = Turno(
        paciente=estudio.paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        estado=Turno.Estado.CONFIRMADO,
        motivo_reserva=_motivo_turno_desde_estudio(estudio),
    )
    turno.full_clean()
    turno.save()

    estudio.turno = turno
    estudio.modificado_por = user
    anterior = aplicar_transicion_estudio(
        estudio,
        accion='asignar_turno',
        nuevo_estado=EstudioComplementario.Estado.CONFIRMADO,
    )
    estudio.save(update_fields=['turno', 'modificado_por', 'updated_at'])
    _auditar_cambio_estado(
        estudio,
        user=user,
        accion='estudio_asignar_turno',
        estado_anterior=anterior,
        estado_nuevo=estudio.estado,
    )
    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=estudio,
        after=safe_model_snapshot(estudio),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_asignar_turno',
            'turno_id': turno.pk,
            **_estudio_meta(estudio),
        },
    )
    return estudio


def _resolver_modalidad_estudio(*, tipo_estudio=None, modalidad=None) -> str:
    if tipo_estudio is not None:
        return tipo_estudio.modalidad
    if modalidad:
        return modalidad
    raise ValidationError(
        {'tipo_estudio': 'Indique el tipo de estudio o la modalidad.'}
    )


@transaction.atomic
def agendar_turno_estudio_desde_agenda(
    *,
    user,
    paciente,
    recurso,
    fecha_hora_inicio,
    fecha_hora_fin,
    estudio=None,
    tipo_estudio=None,
    modalidad=None,
    origen=None,
    descripcion_clinica='',
    medico=None,
):
    """
    Turnera: asigna turno a un estudio ya solicitado o crea uno nuevo
    (p. ej. pedido externo) y lo confirma en la misma operación.
    """
    if estudio is not None:
        if estudio.paciente_id != paciente.id:
            raise ValidationError(
                {'estudio_id': 'El estudio seleccionado no corresponde al paciente.'}
            )
        return asignar_turno_estudio(
            estudio,
            user=user,
            recurso=recurso,
            fecha_hora_inicio=fecha_hora_inicio,
            fecha_hora_fin=fecha_hora_fin,
            medico=medico,
        )

    modalidad_resuelta = _resolver_modalidad_estudio(
        tipo_estudio=tipo_estudio,
        modalidad=modalidad,
    )
    if origen is None:
        origen = EstudioComplementario.Origen.EXTERNO

    nuevo = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'modalidad': modalidad_resuelta,
            'origen': origen,
            'descripcion_clinica': descripcion_clinica or '',
        },
        user=user,
    )
    return asignar_turno_estudio(
        nuevo,
        user=user,
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        medico=medico,
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
    _exigir_estado_estudio(
        estudio,
        _ESTADOS_CREAR_EMITIR_INFORME,
        'Solo se puede crear un informe cuando el estudio está REALIZADO o INFORMADO.',
    )
    informe = InformeEstudioComplementario(
        estudio=estudio,
        version=_siguiente_version_informe(estudio.pk),
        texto=texto or '',
        tipo=tipo,
        creado_por=user,
        es_vigente=False,
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
    estudio = informe.estudio
    if informe.estado != InformeEstudioComplementario.EstadoInforme.BORRADOR:
        raise ValidationError('Solo se puede emitir un informe en borrador.')
    estados_emitir = set(_ESTADOS_CREAR_EMITIR_INFORME)
    if informe.reemplaza_a_id:
        estados_emitir |= {
            EstudioComplementario.Estado.VALIDADO,
            EstudioComplementario.Estado.ENTREGADO,
        }
    _exigir_estado_estudio(
        estudio,
        frozenset(estados_emitir),
        'Solo se puede emitir un informe cuando el estudio está en un estado compatible.',
    )
    if estudio.estado in (
        EstudioComplementario.Estado.ENTREGADO,
        EstudioComplementario.Estado.VALIDADO,
    ) and not informe.reemplaza_a_id:
        raise ValidationError(
            'No se puede emitir un informe nuevo en un estudio validado/entregado sin rectificación.'
        )
    informe.estado = InformeEstudioComplementario.EstadoInforme.EMITIDO
    informe.fecha_informe = timezone.now()
    if medico:
        informe.informado_por = medico
    informe.save()
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
    elif estudio.estado in (
        EstudioComplementario.Estado.ENTREGADO,
        EstudioComplementario.Estado.VALIDADO,
    ) and informe.reemplaza_a_id:
        accion = (
            'rectificar'
            if estudio.estado == EstudioComplementario.Estado.VALIDADO
            else 'informar'
        )
        anterior = aplicar_transicion_estudio(
            estudio,
            accion=accion,
            nuevo_estado=EstudioComplementario.Estado.INFORMADO,
            permitir_reapertura_por_rectificacion=True,
        )
        _auditar_cambio_estado(
            estudio,
            user=user,
            accion='estudio_estado_cambio',
            estado_anterior=anterior,
            estado_nuevo=estudio.estado,
        )
        if informe.reemplaza_a_id:
            _safe_audit(
                log_event,
                action='UPDATE',
                actor=user,
                entity=estudio,
                after=safe_model_snapshot(estudio),
                entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
                module='estudios',
                metadata={
                    'accion': 'estudio_rectificacion_emitir',
                    'view': 'EstudioComplementarioViewSet.emitir_informe',
                    'informe_id': informe.pk,
                    'version_informe': informe.version,
                    'estado_anterior': anterior,
                    'estado_nuevo': estudio.estado,
                    **_estudio_meta(estudio),
                },
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
    estudio = (
        EstudioComplementario.objects.select_for_update()
        .filter(pk=informe.estudio_id)
        .first()
    )
    if not estudio:
        raise ValidationError('Estudio no encontrado.')
    informe = (
        InformeEstudioComplementario.objects.select_for_update()
        .filter(pk=informe.pk, estudio_id=estudio.pk)
        .first()
    )
    if not informe:
        raise ValidationError('Informe no encontrado.')
    if estudio.estado != EstudioComplementario.Estado.INFORMADO:
        raise ValidationError(
            'Solo se puede validar un informe cuando el estudio está INFORMADO.'
        )
    if informe.estudio_id != estudio.pk:
        raise ValidationError('El informe no pertenece a este estudio.')
    otro_vigente_validado = (
        InformeEstudioComplementario.objects.filter(
            estudio=estudio,
            es_vigente=True,
            estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        )
        .exclude(pk=informe.pk)
        .order_by('-version')
        .first()
    )
    if otro_vigente_validado and informe.version < otro_vigente_validado.version:
        raise ValidationError(
            'Ya existe un informe validado vigente más reciente; use rectificación.'
        )
    InformeEstudioComplementario.objects.filter(estudio=estudio).exclude(
        pk=informe.pk
    ).update(es_vigente=False)
    informe.estado = InformeEstudioComplementario.EstadoInforme.VALIDADO
    informe.validado_por = user
    informe.fecha_validacion = timezone.now()
    informe.es_vigente = True
    try:
        informe.save()
    except IntegrityError as exc:
        raise ValidationError(
            'No se pudo dejar un único informe vigente; reintente la operación.'
        ) from exc
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
    motivo: str | None = None,
    motivo_rectificacion: str | None = None,
    texto: str = '',
):
    if informe.estado != InformeEstudioComplementario.EstadoInforme.VALIDADO:
        raise ValidationError('Solo se puede rectificar un informe validado.')
    motivo_final = (motivo_rectificacion or motivo or '').strip()
    if not motivo_final:
        raise ValidationError({'motivo_rectificacion': 'El motivo de rectificación es obligatorio.'})
    estudio = informe.estudio
    if estudio.estado not in (
        EstudioComplementario.Estado.VALIDADO,
        EstudioComplementario.Estado.ENTREGADO,
    ):
        raise ValidationError(
            'La rectificación solo está permitida en estudios VALIDADO o ENTREGADO.'
        )
    if estudio.estado == EstudioComplementario.Estado.ANULADO:
        raise ValidationError('El estudio no admite rectificación en su estado actual.')

    nuevo = InformeEstudioComplementario(
        estudio=estudio,
        version=_siguiente_version_informe(estudio.pk),
        estado=InformeEstudioComplementario.EstadoInforme.BORRADOR,
        tipo=informe.tipo,
        texto=texto or '',
        es_vigente=False,
        reemplaza_a=informe,
        motivo_rectificacion=motivo_final,
        creado_por=user,
    )
    nuevo.save()

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


def servir_descarga_informe_pdf(
    informe: InformeEstudioComplementario,
    *,
    user,
):
    estudio = informe.estudio
    if not usuario_puede_descargar_pdf_informe(user, estudio, informe):
        raise PermissionDenied('No tiene permiso para descargar este informe.')
    if not informe.archivo_pdf:
        raise ValidationError('PDF no disponible para este informe.')

    try:
        storage_path = informe.archivo_pdf.path
    except Exception as exc:
        raise ValidationError('PDF no encontrado en el servidor.') from exc

    if not os.path.exists(storage_path):
        logger.error('PDF de informe ausente en almacenamiento')
        raise ValidationError('PDF no encontrado en el servidor.')

    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=informe,
        after=_informe_snapshot(informe),
        entity_repr=f'estudios.InformeEstudioComplementario:{informe.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_informe_pdf_download',
            'view': 'EstudioComplementarioViewSet.download_pdf_informe',
            'informe_id': informe.pk,
            'version_informe': informe.version,
            **_estudio_meta(estudio),
        },
    )

    response = FileResponse(open(storage_path, 'rb'), content_type='application/pdf')
    nombre = nombre_seguro_pdf_informe(estudio.pk, informe.version)
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response
