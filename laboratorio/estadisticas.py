"""Agregados de volumen LIMS (sin PHI) para Estadísticas."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from django.db.models import Count, F, Q, QuerySet
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.utils import timezone

from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.origen_solicitud import ORIGEN_LABELS


GRANULARIDAD_TRUNC = {
    'dia': TruncDate,
    'mes': TruncMonth,
    'anio': TruncYear,
}


def parse_date(value: str | None, default):
    if not value:
        return default
    return datetime.strptime(value, '%Y-%m-%d').date()


def parse_rango(params) -> tuple:
    hoy = timezone.localdate()
    desde = parse_date(params.get('desde'), hoy - timedelta(days=30))
    hasta = parse_date(params.get('hasta'), hoy)
    if hasta < desde:
        raise ValueError('hasta anterior a desde')
    start = timezone.make_aware(datetime.combine(desde, time.min))
    end = timezone.make_aware(datetime.combine(hasta, time.max))
    return desde, hasta, start, end


def parse_granularidad(params) -> str:
    g = (params.get('granularidad') or 'dia').lower().strip()
    if g in ('año', 'ano', 'year'):
        g = 'anio'
    if g not in GRANULARIDAD_TRUNC:
        raise ValueError('granularidad inválida')
    return g


def _filtros_orden(params) -> Q:
    q = Q()
    estado = (params.get('estado') or '').strip().upper()
    if estado:
        q &= Q(estado=estado)
    origen = (params.get('origen') or '').strip().upper()
    if origen:
        q &= Q(origen_solicitud=origen)
    obra = (params.get('obra_social') or '').strip()
    if obra:
        q &= Q(obra_social_orden__icontains=obra) | (
            (Q(obra_social_orden__isnull=True) | Q(obra_social_orden=''))
            & Q(paciente__obra_social__icontains=obra)
        )
    codigo = (params.get('codigo') or params.get('examen') or '').strip()
    if codigo:
        q &= Q(resultados__tipo_examen__codigo__iexact=codigo)
    return q


def qs_ordenes(start, end, params) -> QuerySet:
    qs = SolicitudExamen.objects.filter(fecha_solicitud__gte=start, fecha_solicitud__lte=end)
    qs = qs.filter(_filtros_orden(params))
    if params.get('codigo') or params.get('examen'):
        qs = qs.distinct()
    return qs


def qs_examenes(start, end, params, *, por_validacion: bool = False) -> QuerySet:
    """Filas ResultadoExamen en rango (por fecha de solicitud u orden, o validación)."""
    if por_validacion:
        qs = ResultadoExamen.objects.filter(
            fecha_validacion__gte=start,
            fecha_validacion__lte=end,
        )
    else:
        qs = ResultadoExamen.objects.filter(
            solicitud__fecha_solicitud__gte=start,
            solicitud__fecha_solicitud__lte=end,
        )
    estado = (params.get('estado') or '').strip().upper()
    if estado:
        qs = qs.filter(solicitud__estado=estado)
    origen = (params.get('origen') or '').strip().upper()
    if origen:
        qs = qs.filter(solicitud__origen_solicitud=origen)
    obra = (params.get('obra_social') or '').strip()
    if obra:
        qs = qs.filter(
            Q(solicitud__obra_social_orden__icontains=obra)
            | (
                (Q(solicitud__obra_social_orden__isnull=True) | Q(solicitud__obra_social_orden=''))
                & Q(solicitud__paciente__obra_social__icontains=obra)
            )
        )
    codigo = (params.get('codigo') or params.get('examen') or '').strip()
    if codigo:
        qs = qs.filter(tipo_examen__codigo__iexact=codigo)
    return qs


def _pct(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * n / total, 1)


def _normalize_os_label(raw: str | None) -> str:
    t = (raw or '').strip()
    return t.upper() if t else '(Sin obra social)'


def resumen(start, end, params) -> dict[str, Any]:
    ordenes = qs_ordenes(start, end, params)
    total_ordenes = ordenes.count()
    examenes = qs_examenes(start, end, params)
    total_examenes = examenes.count()

    por_estado = list(
        ordenes.values('estado').annotate(cantidad=Count('id')).order_by('-cantidad')
    )
    for row in por_estado:
        row['porcentaje'] = _pct(row['cantidad'], total_ordenes)

    top_examenes = list(
        examenes.values(
            codigo=F('tipo_examen__codigo'),
            nombre=F('tipo_examen__nombre'),
        )
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')[:15]
    )
    for row in top_examenes:
        row['porcentaje'] = _pct(row['cantidad'], total_examenes)

    os_counts: dict[str, int] = {}
    for row in ordenes.values('obra_social_orden', 'paciente__obra_social'):
        label = _normalize_os_label(row['obra_social_orden'] or row['paciente__obra_social'])
        os_counts[label] = os_counts.get(label, 0) + 1
    top_os = sorted(
        (
            {'obra_social': k, 'cantidad': v, 'porcentaje': _pct(v, total_ordenes)}
            for k, v in os_counts.items()
        ),
        key=lambda x: -x['cantidad'],
    )[:15]

    return {
        'total_ordenes': total_ordenes,
        'total_examenes': total_examenes,
        'por_estado': por_estado,
        'top_examenes': top_examenes,
        'top_obras_sociales': top_os,
    }


def series(start, end, params, granularidad: str) -> dict[str, Any]:
    trunc = GRANULARIDAD_TRUNC[granularidad]
    ordenes = (
        qs_ordenes(start, end, params)
        .annotate(periodo=trunc('fecha_solicitud'))
        .values('periodo')
        .annotate(cantidad=Count('id'))
        .order_by('periodo')
    )
    examenes = (
        qs_examenes(start, end, params)
        .annotate(periodo=trunc('solicitud__fecha_solicitud'))
        .values('periodo')
        .annotate(cantidad=Count('id'))
        .order_by('periodo')
    )

    def _fmt(p) -> str:
        if p is None:
            return ''
        if granularidad == 'anio':
            return str(p.year)
        if granularidad == 'mes':
            return p.strftime('%Y-%m')
        return p.strftime('%Y-%m-%d')

    ord_map = {_fmt(r['periodo']): r['cantidad'] for r in ordenes}
    ex_map = {_fmt(r['periodo']): r['cantidad'] for r in examenes}
    keys = sorted(set(ord_map) | set(ex_map))
    return {
        'granularidad': granularidad,
        'puntos': [
            {
                'periodo': k,
                'ordenes': ord_map.get(k, 0),
                'examenes': ex_map.get(k, 0),
            }
            for k in keys
        ],
    }


def por_examen(start, end, params) -> dict[str, Any]:
    examenes = qs_examenes(start, end, params)
    total = examenes.count()
    rows = list(
        examenes.values(
            codigo=F('tipo_examen__codigo'),
            nombre=F('tipo_examen__nombre'),
        )
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad', 'codigo')
    )
    for row in rows:
        row['porcentaje'] = _pct(row['cantidad'], total)
    return {'total': total, 'items': rows}


def por_obra_social(start, end, params) -> dict[str, Any]:
    ordenes = qs_ordenes(start, end, params)
    total = ordenes.count()
    counts: dict[str, int] = {}
    for row in ordenes.values('obra_social_orden', 'paciente__obra_social'):
        label = _normalize_os_label(row['obra_social_orden'] or row['paciente__obra_social'])
        counts[label] = counts.get(label, 0) + 1
    items = sorted(
        (
            {'obra_social': k, 'cantidad': v, 'porcentaje': _pct(v, total)}
            for k, v in counts.items()
        ),
        key=lambda x: (-x['cantidad'], x['obra_social']),
    )
    return {'total': total, 'items': items}


def por_origen(start, end, params) -> dict[str, Any]:
    ordenes = qs_ordenes(start, end, params)
    total = ordenes.count()
    rows = list(
        ordenes.values('origen_solicitud').annotate(cantidad=Count('id')).order_by('-cantidad')
    )
    for row in rows:
        origen = row['origen_solicitud'] or ''
        row['origen'] = origen
        row['label'] = ORIGEN_LABELS.get(origen, origen or '(Sin origen)')
        row['porcentaje'] = _pct(row['cantidad'], total)
        del row['origen_solicitud']
    return {'total': total, 'items': rows}


def por_estado(start, end, params) -> dict[str, Any]:
    ordenes = qs_ordenes(start, end, params)
    total = ordenes.count()
    rows = list(ordenes.values('estado').annotate(cantidad=Count('id')).order_by('-cantidad'))
    for row in rows:
        row['porcentaje'] = _pct(row['cantidad'], total)
    return {'total': total, 'items': rows}


def export_rows(start, end, params, dimensiones: str) -> list[dict[str, Any]]:
    """Filas planas para CSV según dimensión."""
    dim = (dimensiones or 'examen').lower()
    if dim in ('obra_social', 'os'):
        return por_obra_social(start, end, params)['items']
    if dim == 'origen':
        return por_origen(start, end, params)['items']
    if dim == 'estado':
        return por_estado(start, end, params)['items']
    if dim == 'serie':
        g = parse_granularidad(params)
        return series(start, end, params, g)['puntos']
    return por_examen(start, end, params)['items']
