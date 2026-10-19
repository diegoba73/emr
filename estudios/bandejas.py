"""Bandejas de listado A5 — filtros read-only sobre estados reales.

Precedencia: ANULADO / ENTREGADO / VALIDADO / REALIZADO|INFORMADO prevalecen
sobre la reserva. “Programado” = reserva vigente (RESERVADO/CONFIRMADO), no FK sola.
GET no repara datos.
"""
from __future__ import annotations

from django.db.models import Exists, OuterRef, Q, QuerySet

BANDEJA_PENDIENTE_PROGRAMAR = 'pendiente_programar'
BANDEJA_PROGRAMADOS = 'programados'
BANDEJA_DOCUMENTACION_PENDIENTE = 'documentacion_pendiente'
BANDEJA_PENDIENTE_ENTREGA = 'pendiente_entrega'
BANDEJA_FINALIZADOS = 'finalizados'
BANDEJA_ANULADOS = 'anulados'
BANDEJA_TODOS = 'todos'

BANDEJAS_VALIDAS = frozenset(
    {
        BANDEJA_PENDIENTE_PROGRAMAR,
        BANDEJA_PROGRAMADOS,
        BANDEJA_DOCUMENTACION_PENDIENTE,
        BANDEJA_PENDIENTE_ENTREGA,
        BANDEJA_FINALIZADOS,
        BANDEJA_ANULADOS,
        BANDEJA_TODOS,
        '',
    }
)

ESTADOS_NO_REALIZADOS = frozenset({'SOLICITADO', 'CONFIRMADO'})
ESTADOS_DOC_PENDIENTE = frozenset({'REALIZADO', 'INFORMADO'})
TURNOS_VIGENTES = frozenset({'RESERVADO', 'CONFIRMADO'})


def _q_reserva_vigente() -> Q:
    from estudios.models import SesionActividad

    sesion_vigente = Exists(
        SesionActividad.objects.filter(
            estudio_id=OuterRef('pk'),
            turno__estado__in=TURNOS_VIGENTES,
        )
    )
    # Exists es Combinable: OR con Q del espejo estudio.turno.
    return Q(turno__estado__in=TURNOS_VIGENTES) | sesion_vigente


def aplicar_bandeja(qs: QuerySet, bandeja: str | None) -> QuerySet:
    """Filtra antes de paginar. Valores desconocidos → sin filtro adicional."""
    key = (bandeja or '').strip().lower()
    if not key or key == BANDEJA_TODOS:
        return qs

    if key == BANDEJA_ANULADOS:
        return qs.filter(estado='ANULADO')
    if key == BANDEJA_FINALIZADOS:
        return qs.filter(estado='ENTREGADO')
    if key == BANDEJA_PENDIENTE_ENTREGA:
        return qs.filter(estado='VALIDADO')
    if key == BANDEJA_DOCUMENTACION_PENDIENTE:
        return qs.filter(estado__in=ESTADOS_DOC_PENDIENTE)

    vigente = _q_reserva_vigente()
    if key == BANDEJA_PROGRAMADOS:
        return qs.filter(estado__in=ESTADOS_NO_REALIZADOS).filter(vigente).distinct()
    if key == BANDEJA_PENDIENTE_PROGRAMAR:
        return (
            qs.filter(estado__in=ESTADOS_NO_REALIZADOS)
            .exclude(vigente)
            .distinct()
        )
    return qs


def conteos_bandejas(qs: QuerySet) -> dict[str, int]:
    """Conteos con el mismo queryset base (permisos + search/práctica ya aplicados)."""
    return {
        BANDEJA_PENDIENTE_PROGRAMAR: aplicar_bandeja(
            qs, BANDEJA_PENDIENTE_PROGRAMAR
        ).count(),
        BANDEJA_PROGRAMADOS: aplicar_bandeja(qs, BANDEJA_PROGRAMADOS).count(),
        BANDEJA_DOCUMENTACION_PENDIENTE: aplicar_bandeja(
            qs, BANDEJA_DOCUMENTACION_PENDIENTE
        ).count(),
        BANDEJA_PENDIENTE_ENTREGA: aplicar_bandeja(
            qs, BANDEJA_PENDIENTE_ENTREGA
        ).count(),
        BANDEJA_FINALIZADOS: aplicar_bandeja(qs, BANDEJA_FINALIZADOS).count(),
        BANDEJA_ANULADOS: aplicar_bandeja(qs, BANDEJA_ANULADOS).count(),
        BANDEJA_TODOS: qs.count(),
    }
