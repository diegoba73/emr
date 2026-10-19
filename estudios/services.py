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
from auditoria.context import get_request_id
from auditoria.models import AuditEvent
from auditoria.snapshot import safe_model_snapshot
import uuid

from .access import (
    usuario_es_realizador_o_admin,
    usuario_puede_cerrar_cirugia,
    usuario_puede_descargar_pdf_informe,
    usuario_puede_entregar_estudio,
    usuario_puede_modificar_contenido_estudio,
    usuario_puede_validar_informe,
)
from .actividad_rules import (
    CAMPOS_A2_PROTEGIDOS,
    ESTADOS_POST_REALIZACION,
    MSG_ANESTESISTA_REQUERIDO,
    MSG_CAMPOS_PROTEGIDOS,
    MSG_CIERRE_PROTOCOLO,
    MSG_DX_PRE_REQUERIDO,
    MSG_ENTREGA_SIN_CIERRE,
    MSG_MULTI_SESION,
    MSG_PROFESIONAL_CIRUGIA_REQUERIDO,
    MSG_PROFESIONAL_REQUERIDO,
    assert_altas_proc_cirugia_deshabilitadas,
    assert_circuito_estudio_legacy,
    assert_no_multi_acciones_legacy,
    assert_paciente_identidad_para_realizacion,
    snapshot_esperado_para,
    validar_correspondencia_actividad,
)
from .estado import aplicar_transicion_estudio
from .models import (
    ArchivoEstudioComplementario,
    EstudioComplementario,
    HistorialCierreEstudioComplementario,
    HistorialEntregaEstudioComplementario,
    HistorialTurnoSesionActividad,
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


def _resolver_estudio_diagnostico(validated_data: dict) -> None:
    """Si no viene FK al catálogo clínico, enlazar por nombre del tipo CEHTA."""
    if validated_data.get('estudio_diagnostico'):
        return
    tipo = validated_data.get('tipo_estudio')
    nombre = getattr(tipo, 'nombre', None) if tipo else None
    if not nombre:
        return
    from catalogos.models import EstudioDiagnostico

    cat = EstudioDiagnostico.objects.filter(nombre__iexact=nombre, activo=True).first()
    if cat:
        validated_data['estudio_diagnostico'] = cat


@transaction.atomic
def crear_estudio(validated_data: dict, *, user) -> EstudioComplementario:
    data = dict(validated_data)
    tipo = data.get('tipo_actividad') or EstudioComplementario.TipoActividad.ESTUDIO
    assert_altas_proc_cirugia_deshabilitadas(tipo)
    if data.get('permite_multi_sesion'):
        raise ValidationError({'permite_multi_sesion': MSG_MULTI_SESION})
    data['permite_multi_sesion'] = False

    if tipo == EstudioComplementario.TipoActividad.PROCEDIMIENTO:
        cat = data.get('procedimiento_catalogo')
        if cat is None:
            raise ValidationError(
                {'procedimiento_catalogo': 'PROCEDIMIENTO exige procedimiento_catalogo.'}
            )
        data['clasificacion_quirurgica_snapshot'] = (
            EstudioComplementario.ClasificacionQuirurgicaSnapshot.NO_QUIRURGICO
        )
        data['tipo_estudio'] = None
        data['practica'] = None
        data['estudio_diagnostico'] = None
        data['cirugia_especialidad'] = None
        data['cirugia_procedimiento'] = None
        data['cirugia_abordaje'] = None
        data['cirugia_especialidad_snapshot'] = ''
        data['cirugia_procedimiento_snapshot'] = ''
        data['cirugia_abordaje_snapshot'] = ''
        data['anestesista_previsto'] = None
        validar_correspondencia_actividad(
            tipo_actividad=tipo,
            procedimiento_catalogo=cat,
            clasificacion_quirurgica_snapshot=data['clasificacion_quirurgica_snapshot'],
            permite_multi_sesion=False,
        )
    elif tipo == EstudioComplementario.TipoActividad.CIRUGIA:
        esp = data.get('cirugia_especialidad')
        proc_c = data.get('cirugia_procedimiento')
        abr = data.get('cirugia_abordaje')
        if esp is None or proc_c is None:
            raise ValidationError(
                {
                    'cirugia_procedimiento': (
                        'CIRUGIA exige especialidad y procedimiento del catálogo quirúrgico.'
                    )
                }
            )
        if data.get('anestesista_previsto') is None:
            raise ValidationError(
                {'anestesista_previsto': 'CIRUGIA exige anestesista previsto en el alta.'}
            )
        data['procedimiento_catalogo'] = None
        data['clasificacion_quirurgica_snapshot'] = (
            EstudioComplementario.ClasificacionQuirurgicaSnapshot.QUIRURGICO
        )
        data['tipo_estudio'] = None
        data['practica'] = None
        data['estudio_diagnostico'] = None
        data['cirugia_especialidad_snapshot'] = getattr(esp, 'nombre', '') or ''
        data['cirugia_procedimiento_snapshot'] = getattr(proc_c, 'nombre', '') or ''
        data['cirugia_abordaje_snapshot'] = getattr(abr, 'nombre', '') or '' if abr else ''
        validar_correspondencia_actividad(
            tipo_actividad=tipo,
            procedimiento_catalogo=None,
            clasificacion_quirurgica_snapshot=data['clasificacion_quirurgica_snapshot'],
            permite_multi_sesion=False,
            cirugia_especialidad=esp,
            cirugia_procedimiento=proc_c,
            cirugia_abordaje=abr,
        )
    else:
        # ESTUDIO (default): estructura limpia sin proc/cirugía.
        data['tipo_actividad'] = EstudioComplementario.TipoActividad.ESTUDIO
        data['procedimiento_catalogo'] = None
        data['cirugia_especialidad'] = None
        data['cirugia_procedimiento'] = None
        data['cirugia_abordaje'] = None
        data['cirugia_especialidad_snapshot'] = ''
        data['cirugia_procedimiento_snapshot'] = ''
        data['cirugia_abordaje_snapshot'] = ''
        data['anestesista_previsto'] = None
        data['clasificacion_quirurgica_snapshot'] = None
        _resolver_estudio_diagnostico(data)

    estudio = EstudioComplementario(**data)
    estudio.creado_por = user
    estudio.modificado_por = user
    if not estudio.fecha_solicitud:
        estudio.fecha_solicitud = timezone.now()
    estudio.full_clean()
    estudio.save()
    from estudios.sesion_sync import crear_sesion_inicial_post_alta

    crear_sesion_inicial_post_alta(estudio)
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


def _assert_puede_modificar_contenido(estudio: EstudioComplementario, user) -> None:
    if not usuario_puede_modificar_contenido_estudio(user, estudio):
        raise PermissionDenied(
            'No tiene permiso para modificar este estudio. '
            'Tras la validación solo puede editarlo quien lo realizó (o un administrador).'
        )


@transaction.atomic
def actualizar_estudio(estudio: EstudioComplementario, validated_data: dict, *, user) -> EstudioComplementario:
    _assert_puede_modificar_contenido(estudio, user)
    if estudio.es_terminal:
        raise ValidationError('El estudio no admite modificaciones en su estado actual.')
    protected_hit = [k for k in CAMPOS_A2_PROTEGIDOS if k in validated_data]
    if protected_hit:
        raise ValidationError({k: MSG_CAMPOS_PROTEGIDOS for k in protected_hit})
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


def _assert_admin(user) -> None:
    rol = str(getattr(user, 'rol', '') or '').lower()
    if not (getattr(user, 'is_superuser', False) or rol == 'admin'):
        raise PermissionDenied('Solo un administrador puede corregir la clasificación.')


@transaction.atomic
def corregir_clasificacion_snapshot(
    estudio: EstudioComplementario,
    *,
    clasificacion_quirurgica_snapshot: str,
    motivo: str,
    user,
) -> EstudioComplementario:
    """A2b: corrección admin compatible con tipo_actividad; TX + audit atómicos."""
    _assert_admin(user)
    motivo_limpio = (motivo or '').strip()
    if not motivo_limpio:
        raise ValidationError({'motivo': 'El motivo es obligatorio.'})

    tipo = estudio.tipo_actividad or EstudioComplementario.TipoActividad.ESTUDIO
    if tipo not in (
        EstudioComplementario.TipoActividad.PROCEDIMIENTO,
        EstudioComplementario.TipoActividad.CIRUGIA,
    ):
        raise ValidationError(
            {'tipo_actividad': 'Solo PROCEDIMIENTO o CIRUGIA admiten corrección de snapshot.'}
        )

    if estudio.estado in ESTADOS_POST_REALIZACION:
        raise ValidationError(
            {
                'estado': (
                    'No se puede corregir la clasificación tras realización, '
                    'informe, validación, entrega o anulación.'
                ),
            }
        )

    esperado = snapshot_esperado_para(tipo)
    snap = (clasificacion_quirurgica_snapshot or '').strip()
    if snap != esperado:
        raise ValidationError(
            {
                'clasificacion_quirurgica_snapshot': (
                    f'Para {tipo} el snapshot debe ser exactamente {esperado}.'
                ),
            }
        )

    before_snap = estudio.clasificacion_quirurgica_snapshot
    before = safe_model_snapshot(estudio)
    estudio.clasificacion_quirurgica_snapshot = snap
    estudio.modificado_por = user
    estudio.full_clean()
    estudio.save(
        update_fields=[
            'clasificacion_quirurgica_snapshot',
            'modificado_por',
            'updated_at',
        ]
    )
    # Audit en la misma TX (create directo: fallo → rollback; no on_commit diferido).
    AuditEvent.objects.create(
        actor_id=getattr(user, 'pk', None),
        action='UPDATE',
        module='estudios',
        entity_type=estudio._meta.label,
        entity_id=str(estudio.pk),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        before_state=before,
        after_state=safe_model_snapshot(estudio),
        request_id=str(get_request_id() or uuid.uuid4()),
        metadata={
            'accion': 'estudio_clasificacion_correccion',
            'view': 'EstudioComplementarioViewSet.corregir_clasificacion_snapshot',
            'motivo': motivo_limpio[:500],
            'snapshot_anterior': before_snap,
            'snapshot_nuevo': snap,
            'tipo_actividad': tipo,
            **_estudio_meta(estudio),
        },
        success=True,
    )
    return estudio


def _auditar_cambio_estado(
    estudio: EstudioComplementario,
    *,
    user,
    accion: str,
    estado_anterior: str,
    estado_nuevo: str,
    extra: dict | None = None,
):
    meta = {
        'accion': accion,
        'view': 'EstudioComplementarioViewSet',
        'estado_anterior': estado_anterior,
        'estado_nuevo': estado_nuevo,
        **_estudio_meta(estudio),
    }
    if extra:
        meta.update(extra)
    _safe_audit(
        log_event,
        action='UPDATE',
        actor=user,
        entity=estudio,
        after=safe_model_snapshot(estudio),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        module='estudios',
        metadata=meta,
    )


_TIPOS_RECURSO_ESTUDIO = frozenset({'SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'})
_TIPOS_RECURSO_CIRUGIA = frozenset({'QUIROFANO', 'SALA_HEMODINAMIA'})


def _recurso_admitido_para_actividad(estudio, recurso) -> bool:
    tipo = getattr(estudio, 'tipo_actividad', None) or EstudioComplementario.TipoActividad.ESTUDIO
    if tipo == EstudioComplementario.TipoActividad.CIRUGIA:
        return recurso.tipo_recurso in _TIPOS_RECURSO_CIRUGIA
    return recurso.tipo_recurso in _TIPOS_RECURSO_ESTUDIO



def _motivo_turno_desde_estudio(estudio: EstudioComplementario) -> str:
    nombre = ''
    if estudio.tipo_actividad == EstudioComplementario.TipoActividad.PROCEDIMIENTO:
        cat = estudio.procedimiento_catalogo
        nombre = getattr(cat, 'nombre', None) or f'Procedimiento #{estudio.pk}'
        return f'Procedimiento: {nombre}'[:255]
    if estudio.tipo_estudio_id and estudio.tipo_estudio:
        nombre = estudio.tipo_estudio.nombre
    if not nombre:
        nombre = estudio.get_practica_display()
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
    sesion_id=None,
):
    from turnos.models import Turno
    from estudios.sesion_sync import resolver_sesion_para_asignacion, sync_asignar_turno_a_sesion

    # Bloqueo consistente: indicación → sesión (A4).
    estudio = EstudioComplementario.objects.select_for_update().get(pk=estudio.pk)
    assert_circuito_estudio_legacy(estudio)
    sesion = resolver_sesion_para_asignacion(estudio, sesion_id)

    multi = bool(estudio.permite_multi_sesion)
    if multi:
        if estudio.estado not in (
            EstudioComplementario.Estado.SOLICITADO,
            EstudioComplementario.Estado.CONFIRMADO,
        ):
            raise ValidationError(
                'Solo se puede asignar turno a estudios en estado Solicitado o Confirmado.'
            )
        if sesion.turno_id:
            raise ValidationError('La sesión ya tiene un turno asignado.')
    else:
        if estudio.estado != EstudioComplementario.Estado.SOLICITADO:
            raise ValidationError('Solo se puede asignar turno a estudios en estado Solicitado.')
        if estudio.turno_id or sesion.turno_id:
            raise ValidationError('El estudio ya tiene un turno asignado.')

    if not _recurso_admitido_para_actividad(estudio, recurso):
        raise ValidationError(
            {'recurso_id': 'El recurso debe ser sala de procedimiento o hemodinamia.'}
        )
    if fecha_hora_fin and fecha_hora_fin <= fecha_hora_inicio:
        raise ValidationError(
            {'fecha_hora_fin': 'La fecha/hora de fin debe ser posterior al inicio.'}
        )

    from estudios.disponibilidad import validar_disponibilidad_reserva_estudio

    validar_disponibilidad_reserva_estudio(
        medico=medico,
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

    estudio.modificado_por = user
    anterior = estudio.estado
    if estudio.estado == EstudioComplementario.Estado.SOLICITADO:
        anterior = aplicar_transicion_estudio(
            estudio,
            accion='asignar_turno',
            nuevo_estado=EstudioComplementario.Estado.CONFIRMADO,
        )
    estudio.save(update_fields=['modificado_por', 'updated_at'])

    sync_asignar_turno_a_sesion(estudio, sesion, turno)

    # Auditoría atómica en TX (rollback si falla — A4).
    AuditEvent.objects.create(
        actor_id=getattr(user, 'pk', None),
        action='UPDATE',
        module='estudios',
        entity_type=estudio._meta.label,
        entity_id=str(estudio.pk),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        after_state=safe_model_snapshot(estudio),
        request_id=str(get_request_id() or uuid.uuid4()),
        metadata={
            'accion': 'estudio_asignar_turno',
            'view': 'EstudioComplementarioViewSet',
            'turno_id': turno.pk,
            'sesion_id': sesion.pk,
            'numero_sesion': sesion.numero_sesion,
            'estado_anterior': anterior,
            'estado_nuevo': estudio.estado,
            **_estudio_meta(estudio),
        },
        success=True,
    )
    return estudio


def _resolver_practica_estudio(*, tipo_estudio=None, practica=None) -> str:
    if tipo_estudio is not None:
        return tipo_estudio.practica
    if practica:
        return practica
    raise ValidationError(
        {'tipo_estudio': 'Indique el tipo de estudio o la práctica.'}
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
    practica=None,
    origen=None,
    descripcion_clinica='',
    medico=None,
    sesion_id=None,
):
    """
    Turnera: asigna turno a un estudio ya solicitado (estudio_id) o crea uno nuevo
    (p. ej. pedido externo) y lo confirma en la misma operación.
    Alta nueva: siempre monosesión. sesion_id solo aplica al camino estudio existente.
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
            sesion_id=sesion_id,
        )

    practica_resuelta = _resolver_practica_estudio(
        tipo_estudio=tipo_estudio,
        practica=practica,
    )
    if origen is None:
        origen = EstudioComplementario.Origen.EXTERNO

    nuevo = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': practica_resuelta,
            'origen': origen,
            'descripcion_clinica': descripcion_clinica or '',
        },
        user=user,
    )
    # Alta nueva: monosesión; no propagar sesion_id (sesión aún no elegible).
    return asignar_turno_estudio(
        nuevo,
        user=user,
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        medico=medico,
    )


@transaction.atomic
def marcar_realizado(
    estudio: EstudioComplementario,
    *,
    user,
    fecha_realizacion=None,
    profesional=None,
    recurso=None,
    anestesista=None,
    diagnostico_preoperatorio: str | None = None,
):
    """
    ESTUDIO: comportamiento previo (realizado_por = actor si no se indica profesional).
    PROCEDIMIENTO (C): profesional obligatorio; Atencion+Registro solo con turno o sala.
    CIRUGIA (D): profesional + anestesista + dx pre; siempre Atencion+RegistroQuirurgico.
    Actor (user) ≠ profesional: secretaría no queda como realizador clínico.
    """
    from estudios.sesion_sync import asegurar_sesion_uno, sync_realizar_sesion_uno
    from estudios.procedimiento_realizacion import ensure_atencion_y_registro_procedimiento
    from estudios.cirugia_realizacion import ensure_atencion_y_registro_quirurgico
    from estudios.access import usuario_puede_marcar_realizado

    estudio = EstudioComplementario.objects.select_for_update().get(pk=estudio.pk)
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    if not usuario_puede_marcar_realizado(user):
        raise PermissionDenied('No tiene permiso para marcar como realizado.')

    if estudio.estado == EstudioComplementario.Estado.REALIZADO:
        # Idempotencia: ya realizado.
        return estudio

    assert_paciente_identidad_para_realizacion(estudio.paciente)

    tipo = estudio.tipo_actividad or EstudioComplementario.TipoActividad.ESTUDIO
    profesional_user = None
    if tipo in (
        EstudioComplementario.TipoActividad.PROCEDIMIENTO,
        EstudioComplementario.TipoActividad.CIRUGIA,
    ):
        msg_prof = (
            MSG_PROFESIONAL_CIRUGIA_REQUERIDO
            if tipo == EstudioComplementario.TipoActividad.CIRUGIA
            else MSG_PROFESIONAL_REQUERIDO
        )
        if profesional is None:
            raise ValidationError({'profesional_id': msg_prof})
        profesional_user = getattr(profesional, 'user', None)
        if profesional_user is None:
            raise ValidationError(
                {
                    'profesional_id': (
                        'El profesional responsable debe tener usuario de sistema '
                        'vinculado para el circuito clínico.'
                    )
                }
            )
        if tipo == EstudioComplementario.TipoActividad.CIRUGIA:
            if anestesista is None:
                raise ValidationError({'anestesista_id': MSG_ANESTESISTA_REQUERIDO})
            if not (diagnostico_preoperatorio or '').strip():
                raise ValidationError({'diagnostico_preoperatorio': MSG_DX_PRE_REQUERIDO})
    elif profesional is not None:
        profesional_user = getattr(profesional, 'user', None) or user
    else:
        profesional_user = user

    from estudios.models import SesionActividad

    sesion = asegurar_sesion_uno(estudio)
    sesion = SesionActividad.objects.select_for_update().filter(pk=sesion.pk).first()

    atencion = None
    registro = None
    if tipo == EstudioComplementario.TipoActividad.PROCEDIMIENTO:
        atencion, registro = ensure_atencion_y_registro_procedimiento(
            estudio=estudio,
            sesion=sesion,
            medico=profesional,
            recurso=recurso,
            actor=user,
        )
        estudio.refresh_from_db()
    elif tipo == EstudioComplementario.TipoActividad.CIRUGIA:
        atencion, registro = ensure_atencion_y_registro_quirurgico(
            estudio=estudio,
            sesion=sesion,
            medico=profesional,
            anestesista=anestesista,
            diagnostico_preoperatorio=diagnostico_preoperatorio or '',
            recurso=recurso,
            actor=user,
        )
        estudio.refresh_from_db()

    estudio.fecha_realizacion = fecha_realizacion or timezone.now()
    estudio.modificado_por = user
    estudio.realizado_por = profesional_user
    estudio.full_clean()
    anterior = aplicar_transicion_estudio(
        estudio,
        accion='marcar_realizado',
        nuevo_estado=EstudioComplementario.Estado.REALIZADO,
    )
    fields = [
        'fecha_realizacion',
        'modificado_por',
        'realizado_por',
        'updated_at',
    ]
    if tipo in (
        EstudioComplementario.TipoActividad.PROCEDIMIENTO,
        EstudioComplementario.TipoActividad.CIRUGIA,
    ):
        fields.insert(-1, 'atencion')
    estudio.save(update_fields=fields)

    sync_realizar_sesion_uno(
        estudio,
        fecha_realizacion=estudio.fecha_realizacion,
        realizado_por=estudio.realizado_por,
    )
    # Auditoría atómica (C/A4/B/D): fallo → rollback de realización/atención/registro.
    AuditEvent.objects.create(
        actor_id=getattr(user, 'pk', None),
        action='UPDATE',
        module='estudios',
        entity_type=estudio._meta.label,
        entity_id=str(estudio.pk),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        after_state=safe_model_snapshot(estudio),
        request_id=str(get_request_id() or uuid.uuid4()),
        metadata={
            'accion': 'estudio_marcar_realizado',
            'view': 'EstudioComplementarioViewSet',
            'estado_anterior': anterior,
            'estado_nuevo': estudio.estado,
            'tipo_actividad': tipo,
            'profesional_id': getattr(profesional, 'pk', None),
            'anestesista_id': getattr(anestesista, 'pk', None),
            'actor_id': getattr(user, 'pk', None),
            'atencion_id': getattr(atencion, 'pk', None),
            'registro_procedimiento_id': (
                getattr(registro, 'pk', None)
                if tipo == EstudioComplementario.TipoActividad.PROCEDIMIENTO
                else None
            ),
            'registro_quirurgico_id': (
                getattr(registro, 'pk', None)
                if tipo == EstudioComplementario.TipoActividad.CIRUGIA
                else None
            ),
            'recurso_id': getattr(recurso, 'pk', None),
            **_estudio_meta(estudio),
        },
        success=True,
    )
    return estudio


@transaction.atomic
def anular_estudio(estudio: EstudioComplementario, *, user, motivo: str):
    """B: anula solicitud previa a realización y libera reserva vigente (CANCELADO)."""
    from turnos.models import Turno
    from turnos import turno_estado
    from estudios.sesion_sync import asegurar_sesion_uno, sync_anular_sesion_uno

    estudio = EstudioComplementario.objects.select_for_update().get(pk=estudio.pk)
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    if not motivo or not str(motivo).strip():
        raise ValidationError({'motivo_anulacion': 'El motivo de anulación es obligatorio.'})
    motivo_limpio = motivo.strip()

    if estudio.estado not in (
        EstudioComplementario.Estado.SOLICITADO,
        EstudioComplementario.Estado.CONFIRMADO,
    ):
        raise ValidationError(
            'Solo se puede anular un estudio en estado Solicitado o Confirmado '
            '(antes de la realización).'
        )

    from estudios.models import SesionActividad

    sesion = asegurar_sesion_uno(estudio)
    sesion = SesionActividad.objects.select_for_update().filter(pk=sesion.pk).first()
    turno_id = sesion.turno_id or estudio.turno_id
    turno = None
    if turno_id:
        turno = Turno.objects.select_for_update().filter(pk=turno_id).first()

    estudio.motivo_anulacion = motivo_limpio
    estudio.modificado_por = user
    anterior = aplicar_transicion_estudio(
        estudio,
        accion='anular',
        nuevo_estado=EstudioComplementario.Estado.ANULADO,
    )
    estudio.save(update_fields=['motivo_anulacion', 'modificado_por', 'updated_at'])
    sync_anular_sesion_uno(estudio)

    if turno is not None and turno.estado in (
        Turno.Estado.RESERVADO,
        Turno.Estado.CONFIRMADO,
        Turno.Estado.DISPONIBLE,
    ):
        turno_estado.cancelar_turno(
            turno,
            actor=user,
            motivo=motivo_limpio,
            view_name='estudios.anular_estudio',
            desde_modulo_estudios=True,
        )

    _auditar_cambio_estado(
        estudio,
        user=user,
        accion='estudio_anular',
        estado_anterior=anterior,
        estado_nuevo=estudio.estado,
    )
    return estudio


@transaction.atomic
def reprogramar_turno_estudio(
    estudio: EstudioComplementario,
    *,
    user,
    recurso,
    fecha_hora_inicio,
    fecha_hora_fin,
    motivo: str,
    medico=None,
    sesion_id=None,
):
    """
    B: turno nuevo + cancelar anterior + historial + sync + auditoría en una TX.
    Fallo → rollback; reserva anterior intacta.
    """
    from turnos.models import Turno
    from turnos import turno_estado
    from estudios.disponibilidad import validar_disponibilidad_reserva_estudio
    from estudios.sesion_sync import (
        resolver_sesion_para_asignacion,
        sincronizar_espejo_turno,
    )

    if not motivo or not str(motivo).strip():
        raise ValidationError({'motivo': 'El motivo de reprogramación es obligatorio.'})
    motivo_limpio = motivo.strip()

    estudio = EstudioComplementario.objects.select_for_update().get(pk=estudio.pk)
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)

    if estudio.estado != EstudioComplementario.Estado.CONFIRMADO:
        raise ValidationError(
            'Solo se puede reprogramar un estudio en estado Confirmado.'
        )

    sesion = resolver_sesion_para_asignacion(estudio, sesion_id)
    if not sesion.turno_id:
        raise ValidationError('La sesión no tiene un turno vigente para reprogramar.')

    turno_anterior = Turno.objects.select_for_update().get(pk=sesion.turno_id)
    if turno_anterior.estado not in (
        Turno.Estado.RESERVADO,
        Turno.Estado.CONFIRMADO,
    ):
        raise ValidationError(
            'No hay una reserva vigente para reprogramar.'
        )

    if not _recurso_admitido_para_actividad(estudio, recurso):
        raise ValidationError(
            {'recurso_id': 'El recurso debe ser sala de procedimiento o hemodinamia.'}
        )

    validar_disponibilidad_reserva_estudio(
        medico=medico if medico is not None else turno_anterior.medico,
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        excluir_turno_id=turno_anterior.pk,
    )

    medico_efectivo = medico if medico is not None else turno_anterior.medico
    turno_nuevo = Turno(
        paciente=estudio.paciente,
        medico=medico_efectivo,
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        estado=Turno.Estado.CONFIRMADO,
        motivo_reserva=_motivo_turno_desde_estudio(estudio),
    )
    turno_nuevo.full_clean()
    turno_nuevo.save()

    turno_estado.cancelar_turno(
        turno_anterior,
        actor=user,
        motivo=motivo_limpio,
        view_name='estudios.reprogramar_turno_estudio',
        desde_modulo_estudios=True,
    )

    from estudios.models import SesionActividad

    sesion.turno = turno_nuevo
    if sesion.estado_sesion == SesionActividad.EstadoSesion.PENDIENTE:
        sesion.estado_sesion = SesionActividad.EstadoSesion.PROGRAMADA
    sesion.save(update_fields=['turno', 'estado_sesion', 'updated_at'])
    sincronizar_espejo_turno(estudio)

    HistorialTurnoSesionActividad.objects.create(
        sesion=sesion,
        turno_anterior=turno_anterior,
        turno_nuevo=turno_nuevo,
        actor=user,
        motivo=motivo_limpio,
    )

    estudio.modificado_por = user
    estudio.save(update_fields=['modificado_por', 'updated_at'])

    AuditEvent.objects.create(
        actor_id=getattr(user, 'pk', None),
        action='UPDATE',
        module='estudios',
        entity_type=estudio._meta.label,
        entity_id=str(estudio.pk),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        after_state=safe_model_snapshot(estudio),
        request_id=str(get_request_id() or uuid.uuid4()),
        metadata={
            'accion': 'estudio_reprogramar_turno',
            'view': 'EstudioComplementarioViewSet',
            'turno_anterior_id': turno_anterior.pk,
            'turno_nuevo_id': turno_nuevo.pk,
            'sesion_id': sesion.pk,
            'numero_sesion': sesion.numero_sesion,
            'motivo': motivo_limpio,
            **_estudio_meta(estudio),
        },
        success=True,
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
    estudio = EstudioComplementario.objects.select_for_update().get(pk=estudio.pk)
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    if not usuario_puede_entregar_estudio(user, estudio):
        raise PermissionDenied('No tiene permiso para entregar este estudio.')
    informe_vig = _informe_vigente_validado(estudio)
    if not informe_vig:
        raise ValidationError('Entregar requiere un informe validado vigente.')
    if estudio.estado != EstudioComplementario.Estado.VALIDADO:
        raise ValidationError('El estudio debe estar en estado VALIDADO para entregar.')

    cierre_hist = None
    if estudio.tipo_actividad == EstudioComplementario.TipoActividad.CIRUGIA:
        if (
            not estudio.protocolo_cierre_informe_id
            or estudio.protocolo_cierre_informe_id != informe_vig.pk
            or not estudio.cerrado_por_id
            or not estudio.fecha_cierre
        ):
            raise ValidationError(MSG_ENTREGA_SIN_CIERRE)
        cierre_hist = (
            HistorialCierreEstudioComplementario.objects.filter(
                estudio=estudio,
                informe_id=informe_vig.pk,
            )
            .order_by('-fecha_cierre', '-id')
            .first()
        )

    anterior = aplicar_transicion_estudio(
        estudio,
        accion='entregar',
        nuevo_estado=EstudioComplementario.Estado.ENTREGADO,
    )
    estudio.modificado_por = user
    estudio.save(update_fields=['modificado_por', 'updated_at'])

    if estudio.tipo_actividad == EstudioComplementario.TipoActividad.CIRUGIA:
        HistorialEntregaEstudioComplementario.objects.create(
            estudio=estudio,
            informe=informe_vig,
            version_protocolo=informe_vig.version,
            entregado_por=user,
            fecha_entrega=timezone.now(),
            cierre=cierre_hist,
        )

    _auditar_cambio_estado(
        estudio,
        user=user,
        accion='estudio_entregar',
        estado_anterior=anterior,
        estado_nuevo=estudio.estado,
    )
    AuditEvent.objects.create(
        actor_id=getattr(user, 'pk', None),
        action='UPDATE',
        module='estudios',
        entity_type=estudio._meta.label,
        entity_id=str(estudio.pk),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        after_state=safe_model_snapshot(estudio),
        request_id=str(get_request_id() or uuid.uuid4()),
        metadata={
            'accion': 'estudio_entregar',
            'view': 'EstudioComplementarioViewSet.entregar',
            'informe_id': informe_vig.pk,
            'version_protocolo': informe_vig.version,
            'cierre_historial_id': getattr(cierre_hist, 'pk', None),
            **_estudio_meta(estudio),
        },
        success=True,
    )
    return estudio


@transaction.atomic
def cerrar_cirugia(estudio: EstudioComplementario, *, user):
    """D: cierre administrativo. Gate: protocolo completo y validado. Idempotente por version."""
    estudio = EstudioComplementario.objects.select_for_update().get(pk=estudio.pk)
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    if estudio.tipo_actividad != EstudioComplementario.TipoActividad.CIRUGIA:
        raise ValidationError({'tipo_actividad': 'El cierre administrativo aplica solo a CIRUGIA.'})
    if not usuario_puede_cerrar_cirugia(user, estudio):
        raise PermissionDenied('No tiene permiso para cerrar esta cirugia.')
    if estudio.estado != EstudioComplementario.Estado.VALIDADO:
        raise ValidationError('La cirugia debe estar VALIDADA para cerrar.')

    informe = (
        InformeEstudioComplementario.objects.select_for_update()
        .filter(
            estudio=estudio,
            es_vigente=True,
            estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        )
        .order_by('-version')
        .first()
    )
    if informe is None or not (informe.texto or '').strip():
        raise ValidationError(MSG_CIERRE_PROTOCOLO)
    if not informe.validado_por_id or not informe.fecha_validacion:
        raise ValidationError(MSG_CIERRE_PROTOCOLO)

    if (
        estudio.protocolo_cierre_informe_id == informe.pk
        and estudio.cerrado_por_id
        and estudio.fecha_cierre
    ):
        return estudio

    ahora = timezone.now()
    hist = HistorialCierreEstudioComplementario.objects.create(
        estudio=estudio,
        informe=informe,
        version_protocolo=informe.version,
        cerrado_por=user,
        fecha_cierre=ahora,
    )
    estudio.cerrado_por = user
    estudio.fecha_cierre = ahora
    estudio.protocolo_cierre_informe = informe
    estudio.modificado_por = user
    estudio.save(
        update_fields=[
            'cerrado_por',
            'fecha_cierre',
            'protocolo_cierre_informe',
            'modificado_por',
            'updated_at',
        ]
    )
    AuditEvent.objects.create(
        actor_id=getattr(user, 'pk', None),
        action='UPDATE',
        module='estudios',
        entity_type=estudio._meta.label,
        entity_id=str(estudio.pk),
        entity_repr=f'estudios.EstudioComplementario:{estudio.pk}',
        after_state=safe_model_snapshot(estudio),
        request_id=str(get_request_id() or uuid.uuid4()),
        metadata={
            'accion': 'estudio_cerrar_cirugia',
            'view': 'EstudioComplementarioViewSet.cerrar',
            'informe_id': informe.pk,
            'version_protocolo': informe.version,
            'validado_por_id': informe.validado_por_id,
            'fecha_validacion': (
                informe.fecha_validacion.isoformat() if informe.fecha_validacion else None
            ),
            'cerrado_por_id': user.pk,
            'fecha_cierre': ahora.isoformat(),
            'historial_cierre_id': hist.pk,
            **_estudio_meta(estudio),
        },
        success=True,
    )
    return estudio


_ORIGENES_ASOCIAR_ARCHIVO = frozenset({
    EstudioComplementario.Origen.EXTERNO,
    EstudioComplementario.Origen.IMPORTADO_HISTORICO,
})


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
    _assert_puede_modificar_contenido(estudio, user)
    if estudio.es_terminal:
        raise ValidationError('No se pueden asociar archivos a un estudio terminal.')
    if estudio.origen not in _ORIGENES_ASOCIAR_ARCHIVO:
        raise ValidationError(
            'Los estudios hechos en la clínica deben subir el archivo desde el estudio '
            '(no asociar desde Archivos). La asociación solo aplica a estudios externos '
            'o importados históricos.'
        )
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


@transaction.atomic
def subir_archivo_estudio(
    estudio: EstudioComplementario,
    *,
    user,
    archivo,
    titulo: str,
    tipo_archivo: str = 'PDF',
    tipo_rol: str = ArchivoEstudioComplementario.TipoRol.OTRO,
    descripcion: str = '',
    orden: int = 0,
    es_principal: bool = False,
) -> ArchivoEstudioComplementario:
    """Crea ArchivoMedico (sin consulta/atención) y lo vincula al estudio."""
    _assert_puede_modificar_contenido(estudio, user)
    if estudio.es_terminal:
        raise ValidationError('No se pueden subir archivos a un estudio terminal.')
    if not archivo:
        raise ValidationError({'archivo': 'Debe adjuntar un archivo.'})

    titulo_clean = (titulo or '').strip() or getattr(archivo, 'name', None) or 'Archivo de estudio'
    tipos_ok = {c[0] for c in ArchivoMedico.TIPO_CHOICES}
    if tipo_archivo not in tipos_ok:
        raise ValidationError({'tipo_archivo': 'Tipo de archivo no válido.'})

    archivo_medico = ArchivoMedico(
        paciente=estudio.paciente,
        titulo=titulo_clean[:200],
        descripcion=descripcion or '',
        tipo_archivo=tipo_archivo,
        archivo=archivo,
        subido_por=user,
    )
    archivo_medico.full_clean()
    archivo_medico.save()

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
            'accion': 'estudio_archivo_subir',
            'view': 'EstudioComplementarioViewSet.subir_archivo',
            'archivo_estudio_id': vinculo.pk,
            'archivo_medico_id': archivo_medico.pk,
            **_estudio_meta(estudio),
        },
    )
    return vinculo


@transaction.atomic
def quitar_archivo_estudio(
    estudio: EstudioComplementario,
    *,
    user,
    archivo_estudio_id: int,
) -> dict:
    """
    Quita el archivo del estudio (elimina el vínculo).

    Si el ArchivoMedico fue subido solo para este estudio (sin consulta/atención
    y sin otros vínculos), también se elimina ese registro para que no reaparezca
    en el menú Archivos. Archivos traídos por el paciente (asociados) solo se
    desvinculan.
    """
    _assert_puede_modificar_contenido(estudio, user)
    if estudio.es_terminal:
        raise ValidationError('No se pueden quitar archivos de un estudio terminal.')
    try:
        vinculo = estudio.archivos_estudio.select_related('archivo_medico').get(
            pk=archivo_estudio_id
        )
    except ArchivoEstudioComplementario.DoesNotExist as exc:
        raise ValidationError({'archivo_estudio_id': 'Archivo no vinculado a este estudio.'}) from exc

    archivo_medico = vinculo.archivo_medico
    archivo_medico_id = archivo_medico.pk
    before = safe_model_snapshot(vinculo)
    _safe_audit(
        log_event,
        action='DELETE',
        actor=user,
        entity=vinculo,
        before=before,
        entity_repr=f'estudios.ArchivoEstudioComplementario:{vinculo.pk}',
        module='estudios',
        metadata={
            'accion': 'estudio_archivo_quitar',
            'view': 'EstudioComplementarioViewSet.quitar_archivo',
            'archivo_estudio_id': vinculo.pk,
            'archivo_medico_id': archivo_medico_id,
            **_estudio_meta(estudio),
        },
    )
    vinculo.delete()

    eliminado_archivo_medico = False
    # Solo borrar el ArchivoMedico si nació como carga del estudio interno
    # (huérfano). Archivos asociados (externos) se desvinculan y quedan en Archivos.
    es_huerfano_estudio = (
        estudio.origen == EstudioComplementario.Origen.INTERNO
        and archivo_medico.consulta_id is None
        and archivo_medico.atencion_id is None
        and not archivo_medico.vinculos_estudio.exists()
    )
    if es_huerfano_estudio:
        before_am = safe_model_snapshot(archivo_medico)
        # Quitar fichero del storage si existe (best-effort).
        try:
            if archivo_medico.archivo:
                archivo_medico.archivo.delete(save=False)
        except Exception:  # pragma: no cover
            logger.exception('No se pudo borrar el fichero físico del ArchivoMedico huérfano')
        archivo_medico.delete()
        eliminado_archivo_medico = True
        _safe_audit(
            log_event,
            action='DELETE',
            actor=user,
            entity=None,
            before=before_am,
            entity_repr=f'archivos_medicos.ArchivoMedico:{archivo_medico_id}',
            module='estudios',
            metadata={
                'accion': 'estudio_archivo_medico_huerfano_eliminar',
                'view': 'EstudioComplementarioViewSet.quitar_archivo',
                'archivo_medico_id': archivo_medico_id,
                **_estudio_meta(estudio),
            },
        )

    return {
        'ok': True,
        'archivo_estudio_id': archivo_estudio_id,
        'archivo_medico_id': archivo_medico_id,
        'archivo_medico_eliminado': eliminado_archivo_medico,
    }


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


def _vincular_informe_a_registro_procedimiento(
    informe: InformeEstudioComplementario,
    estudio: EstudioComplementario,
) -> None:
    """C: canónico = informe; FK al RegistroProcedimiento si existe (sin copiar texto)."""
    if estudio.tipo_actividad != EstudioComplementario.TipoActividad.PROCEDIMIENTO:
        return
    if not estudio.atencion_id:
        return
    from turnos.models import RegistroProcedimiento

    reg = RegistroProcedimiento.objects.filter(pk=estudio.atencion_id).first()
    if reg is None:
        return
    if informe.registro_procedimiento_id != reg.pk:
        informe.registro_procedimiento = reg
        informe.save(update_fields=['registro_procedimiento', 'updated_at'])


def _vincular_informe_a_registro_quirurgico(
    informe: InformeEstudioComplementario,
    estudio: EstudioComplementario,
) -> None:
    """D: canónico = informe; FK al RegistroQuirurgico si existe."""
    if estudio.tipo_actividad != EstudioComplementario.TipoActividad.CIRUGIA:
        return
    if not estudio.atencion_id:
        return
    from turnos.models import RegistroQuirurgico

    reg = RegistroQuirurgico.objects.filter(pk=estudio.atencion_id).first()
    if reg is None:
        return
    if informe.registro_quirurgico_id != reg.pk:
        informe.registro_quirurgico = reg
        informe.save(update_fields=['registro_quirurgico', 'updated_at'])


def _sincronizar_proyeccion_protocolo_cirugia(
    informe: InformeEstudioComplementario,
    estudio: EstudioComplementario,
) -> None:
    """D: unica via de escritura de RegistroQuirurgico.protocolo_quirurgico en circuito modulo."""
    if estudio.tipo_actividad != EstudioComplementario.TipoActividad.CIRUGIA:
        return
    from estudios.cirugia_realizacion import sincronizar_proyeccion_protocolo
    from turnos.models import RegistroQuirurgico

    reg = None
    if informe.registro_quirurgico_id:
        reg = RegistroQuirurgico.objects.filter(pk=informe.registro_quirurgico_id).first()
    elif estudio.atencion_id:
        reg = RegistroQuirurgico.objects.filter(pk=estudio.atencion_id).first()
    if reg is None:
        return
    sincronizar_proyeccion_protocolo(reg, informe.texto or '')


def _invalidar_cierre_actual_cirugia(estudio: EstudioComplementario) -> None:
    """Tras rectificacion: conserva historial; limpia cierre vigente."""
    if estudio.tipo_actividad != EstudioComplementario.TipoActividad.CIRUGIA:
        return
    if not (
        estudio.cerrado_por_id
        or estudio.fecha_cierre
        or estudio.protocolo_cierre_informe_id
    ):
        return
    estudio.cerrado_por = None
    estudio.fecha_cierre = None
    estudio.protocolo_cierre_informe = None
    estudio.save(
        update_fields=[
            'cerrado_por',
            'fecha_cierre',
            'protocolo_cierre_informe',
            'updated_at',
        ]
    )


@transaction.atomic
def crear_informe(
    estudio: EstudioComplementario,
    *,
    user,
    texto: str = '',
    tipo: str = InformeEstudioComplementario.TipoInforme.FINAL,
) -> InformeEstudioComplementario:
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    _assert_puede_modificar_contenido(estudio, user)
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
    _vincular_informe_a_registro_procedimiento(informe, estudio)
    _vincular_informe_a_registro_quirurgico(informe, estudio)
    _sincronizar_proyeccion_protocolo_cirugia(informe, estudio)
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
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    if estudio.estado in (
        EstudioComplementario.Estado.VALIDADO,
        EstudioComplementario.Estado.ENTREGADO,
    ):
        if not usuario_es_realizador_o_admin(user, estudio):
            raise PermissionDenied(
                'Solo quien realizó el estudio o un administrador pueden emitir '
                'la rectificación.'
            )
    else:
        _assert_puede_modificar_contenido(estudio, user)
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
    _vincular_informe_a_registro_procedimiento(informe, estudio)
    _vincular_informe_a_registro_quirurgico(informe, estudio)
    _sincronizar_proyeccion_protocolo_cirugia(informe, estudio)
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
        _invalidar_cierre_actual_cirugia(estudio)
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
    estudio_previo = informe.estudio
    assert_circuito_estudio_legacy(estudio_previo)
    assert_no_multi_acciones_legacy(estudio_previo)
    if not usuario_puede_validar_informe(user, estudio_previo):
        raise PermissionDenied(
            'No tiene permiso para validar este informe. '
            'Solo quien realizó el estudio o un administrador pueden validarlo.'
        )
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
    _vincular_informe_a_registro_quirurgico(informe, estudio)
    _sincronizar_proyeccion_protocolo_cirugia(informe, estudio)
    return informe

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
    estudio = informe.estudio
    assert_circuito_estudio_legacy(estudio)
    assert_no_multi_acciones_legacy(estudio)
    if not usuario_es_realizador_o_admin(user, estudio):
        raise PermissionDenied(
            'Solo quien realizó el estudio o un administrador pueden rectificar el informe.'
        )
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


@transaction.atomic
def enviar_pdf_informe_estudio(informe, *, user):
    """Adjunta el PDF al correo registrado del paciente; no altera el estado clínico."""
    from django.conf import settings
    from django.core.mail import EmailMessage
    from django.core.validators import validate_email
    from .access import usuario_puede_enviar_pdf_informe

    estudio = EstudioComplementario.objects.select_for_update().get(pk=informe.estudio_id)
    informe = InformeEstudioComplementario.objects.select_for_update().get(pk=informe.pk)
    if not usuario_puede_enviar_pdf_informe(user, estudio, informe):
        raise PermissionDenied('Solo se puede enviar un informe validado vigente de un estudio validado o entregado.')
    if settings.EMAIL_BACKEND in {
        'django.core.mail.backends.console.EmailBackend',
        'django.core.mail.backends.dummy.EmailBackend',
        'django.core.mail.backends.filebased.EmailBackend',
    }:
        raise ValidationError('El envío real de correo no está configurado en este entorno.')
    destino = (estudio.paciente.email or '').strip()
    if not destino:
        raise ValidationError('El paciente no tiene correo registrado. Completalo en su ficha antes de enviar.')
    validate_email(destino)
    if not informe.archivo_pdf:
        raise ValidationError('PDF no disponible para este informe.')
    try:
        with informe.archivo_pdf.open('rb') as archivo:
            pdf = archivo.read()
    except (OSError, ValueError) as exc:
        raise ValidationError('No se pudo leer el PDF del informe.') from exc
    mensaje = EmailMessage(
        subject='Informe de estudio disponible',
        body='Adjuntamos el informe de su estudio. Ante cualquier consulta, comuníquese con la institución.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destino],
    )
    mensaje.attach(nombre_seguro_pdf_informe(estudio.pk, informe.version), pdf, 'application/pdf')
    try:
        if mensaje.send(fail_silently=False) != 1:
            raise ValidationError('El servidor de correo no confirmó el envío.')
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError('No se pudo enviar el informe. Revisá la configuración de correo del servidor antes de reintentar.') from exc
    _safe_audit(
        log_event, action='UPDATE', actor=user, entity=informe,
        entity_repr=f'estudios.InformeEstudioComplementario:{informe.pk}',
        module='estudios',
        metadata={'accion': 'estudio_informe_email', 'informe_id': informe.pk,
                  'version_informe': informe.version, **_estudio_meta(estudio)},
    )
