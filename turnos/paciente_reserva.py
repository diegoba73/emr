"""Reglas de reserva del paciente (portal / app móvil)."""
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
