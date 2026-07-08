"""Validación de disponibilidad horaria por recurso (salas de estudio)."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError

from .models import Recurso, Turno

# Separación mínima entre turnos consecutivos en la misma sala (minutos).
BUFFER_MINUTOS_SALA_ESTUDIO = 30

_TIPOS_SALA_ESTUDIO = frozenset({
    Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
    Recurso.TipoRecurso.SALA_HEMODINAMIA,
})

_ESTADOS_OCUPAN_SALA = frozenset({
    Turno.Estado.RESERVADO,
    Turno.Estado.CONFIRMADO,
})


def recurso_es_sala_estudio(recurso) -> bool:
    return recurso is not None and recurso.tipo_recurso in _TIPOS_SALA_ESTUDIO


def validar_disponibilidad_sala_estudio(
    *,
    recurso,
    fecha_hora_inicio: datetime,
    fecha_hora_fin: datetime | None,
    excluir_turno_id: int | None = None,
    buffer_minutos: int = BUFFER_MINUTOS_SALA_ESTUDIO,
) -> None:
    """
    En salas de estudio no puede haber turnos solapados ni separados por menos de
    ``buffer_minutos`` (p. ej. 30 min entre fin de uno e inicio del otro).
    """
    if not recurso_es_sala_estudio(recurso):
        return
    if not fecha_hora_inicio:
        return

    fin = fecha_hora_fin
    if fin is None:
        fin = fecha_hora_inicio + timedelta(minutes=30)
    if fin <= fecha_hora_inicio:
        raise ValidationError(
            {'fecha_hora_fin': 'La fecha/hora de fin debe ser posterior al inicio.'}
        )

    buffer = timedelta(minutes=buffer_minutos)
    ventana_inicio = fecha_hora_inicio - buffer
    ventana_fin = fin + buffer

    qs = Turno.objects.filter(
        recurso=recurso,
        estado__in=_ESTADOS_OCUPAN_SALA,
    )
    if excluir_turno_id:
        qs = qs.exclude(id=excluir_turno_id)

    # Conflicto si la ventana ampliada intersecta [inicio, fin] de otro turno.
    solapados = qs.filter(
        fecha_hora_inicio__lt=ventana_fin,
        fecha_hora_fin__gt=ventana_inicio,
    )
    if not solapados.exists():
        # Turnos sin fecha_hora_fin definida
        solapados = qs.filter(
            fecha_hora_fin__isnull=True,
            fecha_hora_inicio__gte=ventana_inicio,
            fecha_hora_inicio__lt=ventana_fin,
        )

    if solapados.exists():
        otro = solapados.first()
        raise ValidationError(
            {
                'fecha_hora_inicio': (
                    f'La sala "{recurso.nombre}" no está disponible: debe haber al menos '
                    f'{buffer_minutos} minutos libres respecto del turno '
                    f'{otro.fecha_hora_inicio.strftime("%d/%m/%Y %H:%M")}'
                    f'{f"–{otro.fecha_hora_fin.strftime("%H:%M")}" if otro.fecha_hora_fin else ""}.'
                )
            }
        )
