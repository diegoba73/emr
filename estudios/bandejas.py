"""Bandejas de listado A5 — filtros read-only sobre estados reales.

Precedencia: ANULADO / ENTREGADO / VALIDADO / REALIZADO|INFORMADO prevalecen
sobre la reserva. “Programado” = reserva vigente (RESERVADO/CONFIRMADO), no FK sola.
GET no repara datos.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

from django.db.models import DateTimeField, Exists, OuterRef, Q, QuerySet
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

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


def _parse_fecha_param(raw: str | None, *, end_of_day: bool = False) -> Optional[datetime]:
    value = (raw or '').strip()
    if not value:
        return None
    tz = timezone.get_current_timezone()
    # YYYY-MM-DD → día civil local (inicio o fin inclusive).
    if len(value) == 10 and value[4] == '-' and value[7] == '-':
        d = parse_date(value)
        if d is None:
            return None
        start = timezone.make_aware(datetime.combine(d, time.min), tz)
        if end_of_day:
            return start + timedelta(days=1) - timedelta(microseconds=1)
        return start
    dt = parse_datetime(value)
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, tz)
    return dt


def filtrar_por_rango_fechas(
    qs: QuerySet,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> QuerySet:
    """Filtra por fecha de referencia (turno → solicitud → realización → created_at).

    Ítems sin ninguna fecha siguen visibles (p. ej. pendientes de programar).
    Así listado y ``bandejas-resumen`` usan el mismo criterio que la UI.
    """
    desde = _parse_fecha_param(fecha_desde, end_of_day=False)
    hasta = _parse_fecha_param(fecha_hasta, end_of_day=True)
    if desde is None and hasta is None:
        return qs

    qs = qs.annotate(
        _fecha_ref=Coalesce(
            'turno__fecha_hora_inicio',
            'fecha_solicitud',
            'fecha_realizacion',
            'created_at',
            output_field=DateTimeField(),
        )
    )
    # Sin fecha de referencia: no ocultar (alineado al FE).
    q_sin_fecha = Q(_fecha_ref__isnull=True)
    q_rango = Q()
    if desde is not None:
        q_rango &= Q(_fecha_ref__gte=desde)
    if hasta is not None:
        q_rango &= Q(_fecha_ref__lte=hasta)
    return qs.filter(q_sin_fecha | q_rango)


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
