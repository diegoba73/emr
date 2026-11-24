"""Separación mínima entre turnos del mismo paciente según tipo de agenda.

- Dos consultas: ≥ 30 minutos entre el fin de uno y el inicio del otro.
- Consulta + estudio: ≥ 60 minutos.
- Dos estudios: ≥ 60 minutos.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

from turnos.models import Turno

SEPARACION_CONSULTA_MINUTOS = 30
SEPARACION_CONSULTA_ESTUDIO_MINUTOS = 60
SEPARACION_ESTUDIO_ESTUDIO_MINUTOS = 60

ESTADOS_ACTIVOS = (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO)


class SeparacionPacienteError(Exception):
    """El nuevo horario viola la separación mínima con otro turno del paciente."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def tipo_agenda_de_recurso(recurso) -> str:
    from medicos.agenda import tipo_para_recurso

    return tipo_para_recurso(recurso) or 'CONSULTA'


def minutos_separacion_requeridos(tipo_a: str, tipo_b: str) -> int:
    a = (tipo_a or 'CONSULTA').upper()
    b = (tipo_b or 'CONSULTA').upper()
    if a == 'ESTUDIO' and b == 'ESTUDIO':
        return SEPARACION_ESTUDIO_ESTUDIO_MINUTOS
    if a == 'ESTUDIO' or b == 'ESTUDIO':
        return SEPARACION_CONSULTA_ESTUDIO_MINUTOS
    return SEPARACION_CONSULTA_MINUTOS


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _intervalo(inicio: datetime, fin: datetime | None) -> tuple[datetime, datetime]:
    inicio_a = _as_aware(inicio)
    assert inicio_a is not None
    fin_a = _as_aware(fin) if fin else inicio_a
    if fin_a < inicio_a:
        fin_a = inicio_a
    return inicio_a, fin_a


def _gap_entre(a_ini: datetime, a_fin: datetime, b_ini: datetime, b_fin: datetime) -> timedelta:
    """Tiempo libre entre dos intervalos; negativo/cero si se solapan."""
    if a_fin <= b_ini:
        return b_ini - a_fin
    if b_fin <= a_ini:
        return a_ini - b_fin
    return timedelta(0)


def _etiqueta_tipo(tipo: str) -> str:
    return 'estudio' if (tipo or '').upper() == 'ESTUDIO' else 'consulta'


def validar_separacion_paciente(
    *,
    paciente,
    inicio: datetime,
    fin: datetime | None,
    recurso=None,
    tipo_agenda: str | None = None,
    excluir_turno_id: int | None = None,
    estado: str | None = Turno.Estado.RESERVADO,
) -> None:
    """
    Rechaza si el paciente ya tiene un turno activo demasiado cerca.

    Solo aplica a estados RESERVADO/CONFIRMADO (u omitido → se valida).
    """
    if paciente is None:
        return
    if estado is not None and estado not in ESTADOS_ACTIVOS:
        return

    tipo_nuevo = (tipo_agenda or tipo_agenda_de_recurso(recurso) or 'CONSULTA').upper()
    nuevo_ini, nuevo_fin = _intervalo(inicio, fin)

    qs = (
        Turno.objects.filter(
            paciente_id=getattr(paciente, 'pk', paciente),
            estado__in=ESTADOS_ACTIVOS,
        )
        .select_related('recurso')
        .order_by('fecha_hora_inicio')
    )
    if excluir_turno_id:
        qs = qs.exclude(pk=excluir_turno_id)

    for otro in qs.iterator():
        otro_ini, otro_fin = _intervalo(otro.fecha_hora_inicio, otro.fecha_hora_fin)
        tipo_otro = tipo_agenda_de_recurso(otro.recurso)
        requerido = minutos_separacion_requeridos(tipo_nuevo, tipo_otro)
        gap = _gap_entre(nuevo_ini, nuevo_fin, otro_ini, otro_fin)
        if gap < timedelta(minutes=requerido):
            raise SeparacionPacienteError(
                f'Debe haber al menos {requerido} minutos entre este turno '
                f'({_etiqueta_tipo(tipo_nuevo)}) y el otro turno del paciente '
                f'({_etiqueta_tipo(tipo_otro)}, '
                f'{timezone.localtime(otro_ini).strftime("%d/%m/%Y %H:%M")}).'
            )


def mensaje_separacion_o_none(**kwargs: Any) -> str | None:
    try:
        validar_separacion_paciente(**kwargs)
    except SeparacionPacienteError as exc:
        return exc.message
    return None
