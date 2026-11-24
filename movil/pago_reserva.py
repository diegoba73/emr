"""Cobro/garantía de reserva móvil: preparado, inactivo hasta flag."""
from __future__ import annotations

from django.conf import settings
from rest_framework.exceptions import ValidationError


def pago_reserva_habilitado() -> bool:
    return bool(getattr(settings, 'MOBILE_PAGO_RESERVA_ENABLED', False))


def assert_reserva_pago_ok(*, paciente, tipo: str = 'CONSULTA') -> None:
    """
    Gate de cobro antes de crear el turno.

    Con ``MOBILE_PAGO_RESERVA_ENABLED=False`` (default) no hace nada.
    Con flag en True: aún no hay integración MP/transferencia; bloquea con mensaje
    controlado hasta implementar el cobro real.
    """
    if not pago_reserva_habilitado():
        return
    _ = paciente  # reservado para chequear PagoReservaTurno PAGADO
    tipo_norm = (tipo or 'CONSULTA').upper()
    raise ValidationError(
        {
            'detail': (
                'El cobro de reserva está habilitado en este entorno pero la '
                f'integración de pago ({tipo_norm}) aún no está activa. '
                'Contactá a secretaría o desactivá MOBILE_PAGO_RESERVA_ENABLED.'
            )
        }
    )
