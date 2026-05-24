"""Transiciones de estado de EstudioComplementario (C6.4.1)."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from .models import EstudioComplementario

_ALLOWED = frozenset({
    ('marcar_realizado', EstudioComplementario.Estado.SOLICITADO, EstudioComplementario.Estado.REALIZADO),
    ('informar', EstudioComplementario.Estado.REALIZADO, EstudioComplementario.Estado.INFORMADO),
    ('informar', EstudioComplementario.Estado.INFORMADO, EstudioComplementario.Estado.INFORMADO),
    ('validar', EstudioComplementario.Estado.INFORMADO, EstudioComplementario.Estado.VALIDADO),
    ('entregar', EstudioComplementario.Estado.VALIDADO, EstudioComplementario.Estado.ENTREGADO),
    ('anular', EstudioComplementario.Estado.SOLICITADO, EstudioComplementario.Estado.ANULADO),
    ('anular', EstudioComplementario.Estado.REALIZADO, EstudioComplementario.Estado.ANULADO),
    ('anular', EstudioComplementario.Estado.INFORMADO, EstudioComplementario.Estado.ANULADO),
    ('rectificar', EstudioComplementario.Estado.VALIDADO, EstudioComplementario.Estado.INFORMADO),
    ('informar', EstudioComplementario.Estado.ENTREGADO, EstudioComplementario.Estado.INFORMADO),
})

# Excepción explícita: reapertura terminal solo vía emitir rectificación (C6.4.1-B).
_REAPERTURA_RECTIFICACION = frozenset({
    ('informar', EstudioComplementario.Estado.ENTREGADO, EstudioComplementario.Estado.INFORMADO),
    ('rectificar', EstudioComplementario.Estado.VALIDADO, EstudioComplementario.Estado.INFORMADO),
})


class TransicionEstudioNoPermitida(ValidationError):
    pass


def transicion_permitida(accion: str, estado_origen: str, estado_destino: str) -> bool:
    return (accion, estado_origen, estado_destino) in _ALLOWED


def aplicar_transicion_estudio(
    estudio: EstudioComplementario,
    *,
    accion: str,
    nuevo_estado: str,
    permitir_reapertura_por_rectificacion: bool = False,
) -> str:
    anterior = estudio.estado
    es_reapertura_rectificacion = (
        permitir_reapertura_por_rectificacion
        and (accion, anterior, nuevo_estado) in _REAPERTURA_RECTIFICACION
    )
    if (
        estudio.es_terminal
        and accion != 'anular'
        and not es_reapertura_rectificacion
    ):
        raise TransicionEstudioNoPermitida('El estudio no admite cambios en su estado actual.')
    if permitir_reapertura_por_rectificacion and not es_reapertura_rectificacion:
        raise TransicionEstudioNoPermitida(
            'La reapertura por rectificación no aplica a esta transición.'
        )
    if not transicion_permitida(accion, anterior, nuevo_estado):
        raise TransicionEstudioNoPermitida(
            'Transición de estado no permitida para esta acción y estado actual.'
        )
    estudio.estado = nuevo_estado
    estudio.save(update_fields=['estado', 'updated_at'])
    return anterior
