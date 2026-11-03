"""Reglas de reserva del paciente (portal / app móvil)."""
from datetime import timedelta

from django.utils import timezone

from turnos.models import Turno

ESTADOS_TURNO_ACTIVO = (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO)


def turno_activo_futuro(paciente):
    """Próximo turno vigente del paciente (reservado o confirmado), si existe."""
    if paciente is None:
        return None
    return (
        Turno.objects.filter(
            paciente=paciente,
            estado__in=ESTADOS_TURNO_ACTIVO,
            fecha_hora_inicio__gt=timezone.now(),
        )
        .select_related('medico', 'recurso')
        .order_by('fecha_hora_inicio')
        .first()
    )


def estado_inicial_reserva_paciente(inicio) -> str:
    """
    Hoy o mañana (fecha local) → CONFIRMADO.
    Desde pasado mañana → RESERVADO (el paciente debe confirmar desde la app).
    """
    if timezone.is_naive(inicio):
        inicio_local = timezone.make_aware(inicio)
    else:
        inicio_local = timezone.localtime(inicio)
    dia_turno = inicio_local.date()
    hoy = timezone.localdate()
    if dia_turno <= hoy + timedelta(days=1):
        return Turno.Estado.CONFIRMADO
    return Turno.Estado.RESERVADO
