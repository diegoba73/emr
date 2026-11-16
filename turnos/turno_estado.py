"""
Transiciones y acciones operativas de Turno (C5.9.1 / C5.9.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from api.permissions import emr_staff_or_admin_global
from usuarios.roles import ROLES_SECRETARIA_EMR
from medicos.models import Medico

from .access import medico_es_dueno_turno
from .models import Recurso, Turno, Atencion

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
    turno_anterior_id: int | None = None


def _rol_usuario(user) -> str:
    return (getattr(user, 'rol', '') or '').lower()


def puede_gestionar_turnos_global(user) -> bool:
    if emr_staff_or_admin_global(user):
        return True
    return _rol_usuario(user) == 'admin' or _rol_usuario(user) in ROLES_SECRETARIA_EMR


def turno_tiene_atencion_clinica(turno: Turno) -> bool:
    """True si el médico ya inició la atención clínica vinculada al turno."""
    return Atencion.objects.filter(turno_id=turno.pk).exists()


def puede_confirmar_turno(user, turno: Turno) -> bool:
    """Secretaría/admin, o el paciente dueño del turno (RESERVADO→CONFIRMADO)."""
    if puede_gestionar_turnos_global(user):
        return True
    if _rol_usuario(user) != 'paciente':
        return False
    from pacientes.services import ensure_paciente_linked_to_user

    paciente = ensure_paciente_linked_to_user(user)
    return bool(paciente and turno.paciente_id == paciente.pk)


def puede_cancelar_turno(user, turno: Turno) -> bool:
    """Secretaría/admin, o el paciente dueño del turno (futuro RESERVADO/CONFIRMADO)."""
    if puede_gestionar_turnos_global(user):
        return True
    if _rol_usuario(user) != 'paciente':
        return False
    from pacientes.services import ensure_paciente_linked_to_user

    paciente = ensure_paciente_linked_to_user(user)
    if not paciente or turno.paciente_id != paciente.pk:
        return False
    from django.utils import timezone

    return (
        turno.estado in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO)
        and turno.fecha_hora_inicio > timezone.now()
    )


def puede_reprogramar_turno(user, turno: Turno) -> bool:
    """Secretaría/admin, o paciente dueño de turno de estudio agendado desde su pedido."""
    if puede_gestionar_turnos_global(user):
        return True
    if _rol_usuario(user) != 'paciente':
        return False
    from django.utils import timezone
    from pacientes.services import ensure_paciente_linked_to_user
    from estudios.pedido_paciente import turno_viene_de_pedido_paciente

    paciente = ensure_paciente_linked_to_user(user)
    if not paciente or turno.paciente_id != paciente.pk:
        return False
    if turno.estado not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        return False
    if turno.fecha_hora_inicio <= timezone.now():
        return False
    return turno_viene_de_pedido_paciente(turno)


def puede_marcar_realizado_turno(user, turno: Turno) -> bool:
    """Cierre operativo de agenda: solo secretaría/admin (médico usa iniciar-atencion)."""
    return puede_gestionar_turnos_global(user)


def puede_iniciar_atencion_turno(user, turno: Turno) -> bool:
    """C5.10.1: flujo clínico real — médico propio o admin/staff; no secretaría ni paciente."""
    rol = _rol_usuario(user)
    if rol in {'enfermeria', 'laboratorio', 'paciente'} or rol in ROLES_SECRETARIA_EMR:
        return False
    if emr_staff_or_admin_global(user):
        return True
    if rol == 'admin':
        return True
    if rol == 'medico':
        try:
            return medico_es_dueno_turno(user.medico, turno)
        except ObjectDoesNotExist:
            return False
    return False


def puede_marcar_no_asistio_turno(user, turno: Turno) -> bool:
    """No asistencia: solo secretaría/admin."""
    return puede_gestionar_turnos_global(user)


def validate_estado_en_creacion(estado: str | None) -> None:
    """C5.9.2: no crear turnos ya cancelados o realizados por API genérica."""
    if estado in (Turno.Estado.REALIZADO, Turno.Estado.CANCELADO):
        raise TurnoEstadoTransitionError(
            'No se puede crear un turno en estado REALIZADO o CANCELADO. '
            'Use RESERVADO o DISPONIBLE y las acciones de negocio.'
        )


def _parse_dt(value: Any) -> datetime:
    """Parsea fecha/hora; si viene naive (p. ej. `2026-11-16T17:00:00` del FE), la asume en TZ local."""
    if isinstance(value, datetime):
        parsed = value
    elif not value:
        raise TurnoEstadoTransitionError('Fecha/hora inválida.')
    else:
        parsed = parse_datetime(str(value))
        if parsed is None:
            raise TurnoEstadoTransitionError('Fecha/hora inválida.')
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _validar_solapamiento(
    *,
    medico: Medico,
    inicio: datetime,
    fin: datetime | None,
    estado: str,
    excluir_turno_id: int | None,
    es_sobreturno: bool = False,
) -> None:
    if es_sobreturno:
        return
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


def _turno_vinculado_modulo_estudios(turno: Turno) -> bool:
    """True si el turno está ligado a Estudios y procedimientos.

    Incluye: espejo actual, sesión vigente e historial de reprogramaciones
    (turno_anterior / turno_nuevo). No impide consulta histórica (solo mutaciones
    de cancelar/reprogramar por camino genérico).
    """
    try:
        if getattr(turno, 'estudio_complementario', None) is not None:
            return True
    except ObjectDoesNotExist:
        pass
    from estudios.models import HistorialTurnoSesionActividad, SesionActividad
    if SesionActividad.objects.filter(turno_id=turno.pk).exists():
        return True
    return HistorialTurnoSesionActividad.objects.filter(
        Q(turno_anterior_id=turno.pk) | Q(turno_nuevo_id=turno.pk)
    ).exists()


_MSG_OPERAR_DESDE_ESTUDIOS = (
    'Este turno pertenece a Estudios y procedimientos. '
    'Cancelá o reprogramá desde ese módulo.'
)


def cancelar_turno(
    turno: Turno,
    *,
    actor,
    motivo: str,
    view_name: str = 'TurnoViewSet.cancelar',
    desde_modulo_estudios: bool = False,
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

    if not desde_modulo_estudios and _turno_vinculado_modulo_estudios(turno):
        raise TurnoEstadoTransitionError(_MSG_OPERAR_DESDE_ESTUDIOS)

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
    desde_modulo_estudios: bool = False,
) -> TurnoEstadoOutcome:
    """
    Opción 2: turno nuevo en horario libre del médico + cancelar anterior + historial.

    El slot nuevo debe pertenecer a la agenda publicada del médico (si tiene franjas).
    El slot anterior queda libre (turno anterior → CANCELADO) para otro paciente.
    """
    from medicos.agenda import validar_reserva
    from medicos.models import DisponibilidadMedico
    from rest_framework.exceptions import ValidationError as AgendaValidationError

    from .models import HistorialReprogramacionTurno

    motivo_limpio = (motivo or '').strip()
    if not motivo_limpio:
        raise TurnoEstadoTransitionError('El motivo de reprogramación es obligatorio.')

    estado_anterior = turno.estado
    if estado_anterior in (Turno.Estado.CANCELADO, Turno.Estado.REALIZADO):
        raise TurnoEstadoTransitionError(
            f'No se puede reprogramar un turno en estado {estado_anterior}.'
        )
    from estudios.pedido_paciente import turno_viene_de_pedido_paciente

    es_pedido_estudio = turno_viene_de_pedido_paciente(turno)
    if (
        not desde_modulo_estudios
        and not es_pedido_estudio
        and _turno_vinculado_modulo_estudios(turno)
    ):
        raise TurnoEstadoTransitionError(_MSG_OPERAR_DESDE_ESTUDIOS)
    if estado_anterior not in (
        Turno.Estado.DISPONIBLE,
        Turno.Estado.RESERVADO,
        Turno.Estado.CONFIRMADO,
    ):
        raise TurnoEstadoTransitionError(
            f'No se puede reprogramar un turno en estado {estado_anterior}.'
        )
    if turno_tiene_atencion_clinica(turno):
        raise TurnoEstadoTransitionError(
            'No se puede reprogramar un turno con atención clínica iniciada.'
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

    # Paciente: no puede cambiar de médico (ni aunque envíe otro medico_id).
    if rol == 'paciente' and medico is not None and medico.id != turno.medico_id:
        raise TurnoEstadoTransitionError(
            'Solo podés reprogramar con el mismo médico del turno asignado.'
        )

    medico_efectivo = medico or turno.medico
    if medico_efectivo is None:
        raise TurnoEstadoTransitionError('El turno debe tener un médico para reprogramar.')
    if rol == 'paciente':
        medico_efectivo = turno.medico

    # Solo secretaría institucional puede generar/conservar solapamiento al
    # reprogramar (misma regla que el alta de sobreturno). Admin/superuser no.
    from usuarios.roles import es_secretaria_institucional

    permitir_sobreturno = bool(getattr(turno, 'es_sobreturno', False)) and es_secretaria_institucional(
        actor
    )

    agenda_publicada = DisponibilidadMedico.objects.filter(medico=medico_efectivo).exists()
    if not agenda_publicada and not permitir_sobreturno:
        raise TurnoEstadoTransitionError(
            'El médico no tiene horarios de atención publicados. '
            'Configure la agenda antes de reprogramar.'
        )

    from medicos.agenda import recurso_de_franja_publicada, tipo_para_recurso
    from django.core.exceptions import ValidationError as DjangoValidationError

    def _agenda_err(exc: AgendaValidationError) -> TurnoEstadoTransitionError:
        detail = exc.detail
        if isinstance(detail, dict):
            parts = []
            for key, val in detail.items():
                if isinstance(val, (list, tuple)):
                    parts.extend(str(v) for v in val)
                else:
                    parts.append(str(val))
            return TurnoEstadoTransitionError(' '.join(parts) if parts else str(detail))
        return TurnoEstadoTransitionError(str(detail))

    tipo_franja_requerido = None
    if es_pedido_estudio or rol == 'paciente':
        tipo_franja_requerido = 'ESTUDIO'

    # Consultorio/sala del nuevo horario = el de la franja del médico (no elección libre).
    recurso_efectivo = recurso if recurso is not None else turno.recurso
    if agenda_publicada:
        try:
            recurso_efectivo = recurso_de_franja_publicada(
                medico_efectivo,
                inicio,
                fin,
                tipo=tipo_franja_requerido,
                recurso_solicitado=recurso if recurso is not None else None,
            )
        except AgendaValidationError as exc:
            raise _agenda_err(exc) from exc

    tipo_franja_resuelto = tipo_para_recurso(recurso_efectivo)
    if tipo_franja_requerido and tipo_franja_resuelto != tipo_franja_requerido:
        raise TurnoEstadoTransitionError(
            'Elegí un horario de estudio del mismo médico, no una consulta.'
        )

    try:
        from estudios.pedido_paciente import validar_reprogramacion_estudio

        validar_reprogramacion_estudio(
            turno,
            actor=actor,
            medico=medico_efectivo,
            recurso=recurso_efectivo,
            tipo_franja=tipo_franja_resuelto,
        )
    except DjangoValidationError as exc:
        messages = getattr(exc, 'messages', None)
        if messages:
            raise TurnoEstadoTransitionError(' '.join(str(m) for m in messages)) from exc
        detail = getattr(exc, 'message_dict', None) or getattr(exc, 'detail', None) or str(exc)
        if isinstance(detail, dict):
            parts = []
            for val in detail.values():
                if isinstance(val, (list, tuple)):
                    parts.extend(str(v) for v in val)
                else:
                    parts.append(str(val))
            raise TurnoEstadoTransitionError(' '.join(parts) if parts else str(detail)) from exc
        raise TurnoEstadoTransitionError(str(detail)) from exc

    try:
        # Franja publicada del médico (no cualquier horario). Sobreturno conserva excepción.
        validar_reserva(
            medico_efectivo,
            inicio,
            fin,
            recurso_efectivo,
            excluir=turno.pk,
            exigir_horario=not permitir_sobreturno,
            permitir_sobreturno=permitir_sobreturno,
        )
    except AgendaValidationError as exc:
        raise _agenda_err(exc) from exc

    _validar_solapamiento(
        medico=medico_efectivo,
        inicio=inicio,
        fin=fin,
        estado=estado_anterior if estado_anterior in (
            Turno.Estado.RESERVADO,
            Turno.Estado.CONFIRMADO,
        ) else Turno.Estado.RESERVADO,
        excluir_turno_id=turno.pk,
        es_sobreturno=permitir_sobreturno,
    )

    before = safe_model_snapshot(turno)
    inicio_ant = turno.fecha_hora_inicio
    fin_ant = turno.fecha_hora_fin
    medico_id_ant = turno.medico_id
    recurso_id_ant = turno.recurso_id
    turno_anterior_id = turno.pk

    estado_nuevo_turno = (
        estado_anterior
        if estado_anterior != Turno.Estado.DISPONIBLE
        else Turno.Estado.RESERVADO
    )

    with transaction.atomic():
        turno_nuevo = Turno(
            paciente=turno.paciente,
            medico=medico_efectivo,
            recurso=recurso_efectivo,
            fecha_hora_inicio=inicio,
            fecha_hora_fin=fin,
            estado=estado_nuevo_turno,
            motivo_reserva=turno.motivo_reserva,
            es_sobreturno=permitir_sobreturno,
        )
        try:
            turno_nuevo.full_clean()
        except ValidationError as exc:
            raise TurnoEstadoTransitionError(str(exc)) from exc
        turno_nuevo.save()

        cancelar_turno(
            turno,
            actor=actor,
            motivo=motivo_limpio,
            view_name=view_name,
            desde_modulo_estudios=desde_modulo_estudios or es_pedido_estudio,
        )

        if es_pedido_estudio:
            from estudios.models import (
                EstudioComplementario,
                PedidoEstudioPaciente,
                SesionActividad,
            )

            PedidoEstudioPaciente.objects.filter(turno_id=turno_anterior_id).update(
                turno=turno_nuevo
            )
            EstudioComplementario.objects.filter(turno_id=turno_anterior_id).update(
                turno=turno_nuevo
            )
            SesionActividad.objects.filter(turno_id=turno_anterior_id).update(
                turno=turno_nuevo
            )

        HistorialReprogramacionTurno.objects.create(
            turno_anterior_id=turno_anterior_id,
            turno_nuevo=turno_nuevo,
            actor=actor if getattr(actor, 'pk', None) else None,
            motivo=motivo_limpio,
        )

        _audit_transition(
            turno=turno_nuevo,
            before=before,
            actor=actor,
            accion='reprogramar_turno',
            estado_anterior=estado_anterior,
            estado_nuevo=turno_nuevo.estado,
            view_name=view_name,
            motivo=motivo_limpio,
            extra_metadata={
                'turno_anterior_id': turno_anterior_id,
                'turno_nuevo_id': turno_nuevo.pk,
                'fecha_hora_inicio_anterior': inicio_ant.isoformat() if inicio_ant else None,
                'fecha_hora_inicio_nueva': turno_nuevo.fecha_hora_inicio.isoformat(),
                'fecha_hora_fin_anterior': fin_ant.isoformat() if fin_ant else None,
                'fecha_hora_fin_nueva': (
                    turno_nuevo.fecha_hora_fin.isoformat() if turno_nuevo.fecha_hora_fin else None
                ),
                'medico_id_anterior': medico_id_ant,
                'medico_id_nuevo': turno_nuevo.medico_id,
                'recurso_id_anterior': recurso_id_ant,
                'recurso_id_nuevo': turno_nuevo.recurso_id,
                'viene_de_pedido_estudio': es_pedido_estudio,
            },
        )
    return TurnoEstadoOutcome(
        turno=turno_nuevo,
        estado_anterior=estado_anterior,
        estado_nuevo=turno_nuevo.estado,
        applied=True,
        message='Turno reprogramado exitosamente.',
        turno_anterior_id=turno_anterior_id,
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
