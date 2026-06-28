"""
Transiciones y acciones operativas de Turno (C5.9.1 / C5.9.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.dateparse import parse_datetime

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from api.permissions import emr_staff_or_admin_global
from medicos.models import Medico
from pacientes.services import ensure_paciente_linked_to_user

from .models import Recurso, Turno

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class TurnoEstadoTransitionError(ValueError):
    """Transición de estado no permitida o estado terminal incompatible."""


@dataclass(frozen=True)
class TurnoEstadoOutcome:
    turno: Turno
    estado_anterior: str
    estado_nuevo: str
    applied: bool
    message: str


def _rol_usuario(user) -> str:
    return (getattr(user, 'rol', '') or '').lower()


def puede_gestionar_turnos_global(user) -> bool:
    if emr_staff_or_admin_global(user):
        return True
    return _rol_usuario(user) in {'admin', 'secretaria'}


def puede_confirmar_turno(user, turno: Turno) -> bool:
    if puede_gestionar_turnos_global(user):
        return True
    if _rol_usuario(user) != 'medico':
        return False
    try:
        return turno.medico_id == user.medico.id
    except ObjectDoesNotExist:
        return False


def puede_cancelar_turno(user, turno: Turno) -> bool:
    if puede_gestionar_turnos_global(user):
        return True
    rol = _rol_usuario(user)
    if rol == 'medico':
        try:
            return turno.medico_id == user.medico.id
        except ObjectDoesNotExist:
            return False
    if rol == 'paciente':
        pac = ensure_paciente_linked_to_user(user)
        return bool(pac and turno.paciente_id == pac.id)
    return False


def puede_reprogramar_turno(user, turno: Turno) -> bool:
    if _rol_usuario(user) in {'enfermeria', 'laboratorio'}:
        return False
    if puede_gestionar_turnos_global(user):
        return True
    rol = _rol_usuario(user)
    if rol == 'medico':
        try:
            return turno.medico_id == user.medico.id
        except ObjectDoesNotExist:
            return False
    if rol == 'paciente':
        pac = ensure_paciente_linked_to_user(user)
        return bool(pac and turno.paciente_id == pac.id)
    return False


def puede_marcar_realizado_turno(user, turno: Turno) -> bool:
    if _rol_usuario(user) in {'enfermeria', 'laboratorio', 'paciente'}:
        return False
    if puede_gestionar_turnos_global(user):
        return True
    if _rol_usuario(user) == 'medico':
        try:
            return (
                turno.medico_id == user.medico.id
                and turno.estado == Turno.Estado.CONFIRMADO
            )
        except ObjectDoesNotExist:
            return False
    return False


def puede_iniciar_atencion_turno(user, turno: Turno) -> bool:
    """C5.10.1: flujo clínico real — médico propio o admin/staff; no secretaría ni paciente."""
    rol = _rol_usuario(user)
    if rol in {'enfermeria', 'laboratorio', 'paciente', 'secretaria'}:
        return False
    if emr_staff_or_admin_global(user):
        return True
    if rol == 'admin':
        return True
    if rol == 'medico':
        try:
            return turno.medico_id == user.medico.id
        except ObjectDoesNotExist:
            return False
    return False


def puede_marcar_no_asistio_turno(user, turno: Turno) -> bool:
    if _rol_usuario(user) in {'enfermeria', 'laboratorio', 'paciente'}:
        return False
    if puede_gestionar_turnos_global(user):
        return True
    if _rol_usuario(user) == 'medico':
        try:
            return turno.medico_id == user.medico.id
        except ObjectDoesNotExist:
            return False
    return False


def validate_estado_en_creacion(estado: str | None) -> None:
    """C5.9.2: no crear turnos ya cancelados o realizados por API genérica."""
    if estado in (Turno.Estado.REALIZADO, Turno.Estado.CANCELADO):
        raise TurnoEstadoTransitionError(
            'No se puede crear un turno en estado REALIZADO o CANCELADO. '
            'Use RESERVADO o DISPONIBLE y las acciones de negocio.'
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        raise TurnoEstadoTransitionError('Fecha/hora inválida.')
    parsed = parse_datetime(str(value))
    if parsed is None:
        raise TurnoEstadoTransitionError('Fecha/hora inválida.')
    return parsed


def _validar_solapamiento(
    *,
    medico: Medico,
    inicio: datetime,
    fin: datetime | None,
    estado: str,
    excluir_turno_id: int | None,
) -> None:
    if estado not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        return
    qs = Turno.objects.filter(
        medico=medico,
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
    )
    if excluir_turno_id:
        qs = qs.exclude(id=excluir_turno_id)
    if fin:
        solapados = qs.filter(fecha_hora_inicio__lt=fin, fecha_hora_fin__gt=inicio)
    else:
        solapados = qs.filter(
            fecha_hora_inicio__lte=inicio,
            fecha_hora_fin__gte=inicio,
        )
    if solapados.exists():
        otro = solapados.first()
        raise TurnoEstadoTransitionError(
            f'Ya existe un turno {otro.get_estado_display()} para este médico '
            f'en el rango horario especificado.'
        )


def _audit_transition(
    *,
    turno: Turno,
    before: dict,
    actor,
    accion: str,
    estado_anterior: str,
    estado_nuevo: str,
    view_name: str,
    motivo: str | None = None,
    extra_metadata: dict | None = None,
) -> None:
    metadata = {
        'accion': accion,
        'estado_anterior': estado_anterior,
        'estado_nuevo': estado_nuevo,
        'turno_id': turno.pk,
        'view': view_name,
    }
    if motivo is not None:
        metadata['motivo'] = motivo
    if extra_metadata:
        metadata.update(extra_metadata)
    log_update(
        actor=actor,
        entity=turno,
        before=before,
        module='turnos',
        metadata=metadata,
    )


def confirmar_turno(
    turno: Turno,
    *,
    actor,
    view_name: str = 'TurnoViewSet.confirmar',
) -> TurnoEstadoOutcome:
    estado_anterior = turno.estado

    if estado_anterior == Turno.Estado.CONFIRMADO:
        return TurnoEstadoOutcome(
            turno=turno,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_anterior,
            applied=False,
            message='El turno ya está confirmado.',
        )

    if estado_anterior in (Turno.Estado.CANCELADO, Turno.Estado.REALIZADO):
        raise TurnoEstadoTransitionError(
            f'No se puede confirmar un turno en estado {estado_anterior}.'
        )

    if estado_anterior != Turno.Estado.RESERVADO:
        raise TurnoEstadoTransitionError(
            f'Solo se pueden confirmar turnos en estado {Turno.Estado.RESERVADO}. '
            f'Estado actual: {estado_anterior}.'
        )

    before = safe_model_snapshot(turno)
    turno.estado = Turno.Estado.CONFIRMADO
    turno.save(update_fields=['estado', 'updated_at'])
    _audit_transition(
        turno=turno,
        before=before,
        actor=actor,
        accion='confirmar_turno',
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        view_name=view_name,
    )
    return TurnoEstadoOutcome(
        turno=turno,
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        applied=True,
        message='Turno confirmado exitosamente.',
    )


def cancelar_turno(
    turno: Turno,
    *,
    actor,
    motivo: str,
    view_name: str = 'TurnoViewSet.cancelar',
) -> TurnoEstadoOutcome:
    motivo_limpio = (motivo or '').strip()
    if not motivo_limpio:
        raise TurnoEstadoTransitionError('El motivo de cancelación es obligatorio.')

    estado_anterior = turno.estado

    if estado_anterior == Turno.Estado.CANCELADO:
        return TurnoEstadoOutcome(
            turno=turno,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_anterior,
            applied=False,
            message='El turno ya está cancelado.',
        )

    if estado_anterior == Turno.Estado.REALIZADO:
        raise TurnoEstadoTransitionError(
            'No se puede cancelar un turno en estado REALIZADO.'
        )

    if estado_anterior not in (
        Turno.Estado.DISPONIBLE,
        Turno.Estado.RESERVADO,
        Turno.Estado.CONFIRMADO,
    ):
        raise TurnoEstadoTransitionError(
            f'No se puede cancelar un turno en estado {estado_anterior}.'
        )

    before = safe_model_snapshot(turno)
    turno.estado = Turno.Estado.CANCELADO
    turno.save(update_fields=['estado', 'updated_at'])
    _audit_transition(
        turno=turno,
        before=before,
        actor=actor,
        accion='cancelar_turno',
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        view_name=view_name,
        motivo=motivo_limpio,
    )
    return TurnoEstadoOutcome(
        turno=turno,
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        applied=True,
        message='Turno cancelado exitosamente.',
    )


def reprogramar_turno(
    turno: Turno,
    *,
    actor,
    fecha_hora_inicio,
    fecha_hora_fin,
    motivo: str,
    medico: Medico | None = None,
    recurso: Recurso | None = None,
    view_name: str = 'TurnoViewSet.reprogramar',
) -> TurnoEstadoOutcome:
    motivo_limpio = (motivo or '').strip()
    if not motivo_limpio:
        raise TurnoEstadoTransitionError('El motivo de reprogramación es obligatorio.')

    estado_anterior = turno.estado
    if estado_anterior in (Turno.Estado.CANCELADO, Turno.Estado.REALIZADO):
        raise TurnoEstadoTransitionError(
            f'No se puede reprogramar un turno en estado {estado_anterior}.'
        )
    if estado_anterior not in (
        Turno.Estado.DISPONIBLE,
        Turno.Estado.RESERVADO,
        Turno.Estado.CONFIRMADO,
    ):
        raise TurnoEstadoTransitionError(
            f'No se puede reprogramar un turno en estado {estado_anterior}.'
        )

    inicio = _parse_dt(fecha_hora_inicio)
    fin = _parse_dt(fecha_hora_fin)
    if fin <= inicio:
        raise TurnoEstadoTransitionError(
            'La fecha/hora de fin debe ser posterior a la fecha/hora de inicio.'
        )

    rol = _rol_usuario(actor)
    if rol == 'medico' and medico and medico.id != turno.medico_id:
        raise TurnoEstadoTransitionError('No puede reasignar el turno a otro médico.')

    medico_efectivo = medico or turno.medico
    recurso_efectivo = recurso if recurso is not None else turno.recurso

    before = safe_model_snapshot(turno)
    inicio_ant = turno.fecha_hora_inicio
    fin_ant = turno.fecha_hora_fin
    medico_id_ant = turno.medico_id
    recurso_id_ant = turno.recurso_id

    turno.fecha_hora_inicio = inicio
    turno.fecha_hora_fin = fin
    if medico is not None:
        turno.medico = medico
    if recurso is not None:
        turno.recurso = recurso

    _validar_solapamiento(
        medico=medico_efectivo,
        inicio=turno.fecha_hora_inicio,
        fin=turno.fecha_hora_fin,
        estado=turno.estado,
        excluir_turno_id=turno.pk,
    )

    try:
        turno.full_clean()
    except ValidationError as exc:
        raise TurnoEstadoTransitionError(str(exc)) from exc

    turno.save(
        update_fields=[
            'fecha_hora_inicio',
            'fecha_hora_fin',
            'medico',
            'recurso',
            'updated_at',
        ]
    )

    _audit_transition(
        turno=turno,
        before=before,
        actor=actor,
        accion='reprogramar_turno',
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        view_name=view_name,
        motivo=motivo_limpio,
        extra_metadata={
            'fecha_hora_inicio_anterior': inicio_ant.isoformat() if inicio_ant else None,
            'fecha_hora_inicio_nueva': turno.fecha_hora_inicio.isoformat(),
            'fecha_hora_fin_anterior': fin_ant.isoformat() if fin_ant else None,
            'fecha_hora_fin_nueva': turno.fecha_hora_fin.isoformat() if turno.fecha_hora_fin else None,
            'medico_id_anterior': medico_id_ant,
            'medico_id_nuevo': turno.medico_id,
            'recurso_id_anterior': recurso_id_ant,
            'recurso_id_nuevo': turno.recurso_id,
        },
    )
    return TurnoEstadoOutcome(
        turno=turno,
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        applied=True,
        message='Turno reprogramado exitosamente.',
    )


def marcar_realizado_turno(
    turno: Turno,
    *,
    actor,
    motivo: str | None = None,
    view_name: str = 'TurnoViewSet.marcar_realizado',
) -> TurnoEstadoOutcome:
    estado_anterior = turno.estado

    if estado_anterior == Turno.Estado.REALIZADO:
        return TurnoEstadoOutcome(
            turno=turno,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_anterior,
            applied=False,
            message='El turno ya está realizado.',
        )

    if estado_anterior == Turno.Estado.CANCELADO:
        raise TurnoEstadoTransitionError(
            'No se puede marcar como realizado un turno cancelado.'
        )

    if estado_anterior == Turno.Estado.DISPONIBLE:
        raise TurnoEstadoTransitionError(
            'No se puede marcar como realizado un turno en estado DISPONIBLE.'
        )

    if estado_anterior == Turno.Estado.RESERVADO:
        if not puede_gestionar_turnos_global(actor):
            raise TurnoEstadoTransitionError(
                'Solo administración o secretaría pueden marcar realizado desde RESERVADO.'
            )

    if estado_anterior not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        raise TurnoEstadoTransitionError(
            f'No se puede marcar como realizado desde estado {estado_anterior}.'
        )

    before = safe_model_snapshot(turno)
    turno.estado = Turno.Estado.REALIZADO
    turno.save(update_fields=['estado', 'updated_at'])
    meta: dict = {}
    if motivo and motivo.strip():
        meta['motivo'] = motivo.strip()
    _audit_transition(
        turno=turno,
        before=before,
        actor=actor,
        accion='marcar_realizado_turno',
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        view_name=view_name,
        motivo=meta.get('motivo'),
        extra_metadata=meta if meta else None,
    )
    return TurnoEstadoOutcome(
        turno=turno,
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        applied=True,
        message='Turno marcado como realizado.',
    )


def marcar_no_asistio_turno(
    turno: Turno,
    *,
    actor,
    motivo: str,
    view_name: str = 'TurnoViewSet.marcar_no_asistio',
) -> TurnoEstadoOutcome:
    motivo_limpio = (motivo or '').strip()
    if not motivo_limpio:
        raise TurnoEstadoTransitionError('El motivo es obligatorio para registrar no asistencia.')

    estado_anterior = turno.estado

    if estado_anterior == Turno.Estado.CANCELADO:
        raise TurnoEstadoTransitionError(
            'El turno ya está cancelado. No se puede distinguir no asistencia sin campo estructural.'
        )

    if estado_anterior == Turno.Estado.REALIZADO:
        raise TurnoEstadoTransitionError(
            'No se puede registrar no asistencia en un turno realizado.'
        )

    if estado_anterior not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        raise TurnoEstadoTransitionError(
            f'No se puede registrar no asistencia desde estado {estado_anterior}.'
        )

    before = safe_model_snapshot(turno)
    turno.estado = Turno.Estado.CANCELADO
    turno.save(update_fields=['estado', 'updated_at'])
    _audit_transition(
        turno=turno,
        before=before,
        actor=actor,
        accion='marcar_no_asistio',
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        view_name=view_name,
        motivo=motivo_limpio,
    )
    return TurnoEstadoOutcome(
        turno=turno,
        estado_anterior=estado_anterior,
        estado_nuevo=turno.estado,
        applied=True,
        message='No asistencia registrada; turno cancelado.',
    )
