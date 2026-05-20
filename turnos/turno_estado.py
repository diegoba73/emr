"""
Transiciones de estado controladas para Turno (C5.9.1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from pacientes.services import ensure_paciente_linked_to_user

from .models import Turno

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
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
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
