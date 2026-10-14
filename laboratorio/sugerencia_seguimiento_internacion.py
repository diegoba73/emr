"""Ensayos pedidos en internación recientes (sugerencia suave al crear orden)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from laboratorio.models import SolicitudExamen
from laboratorio.origen_solicitud import INTERNACION_UCE, INTERNACION_UCO

ORIGENES_INTERNACION = frozenset({INTERNACION_UCO, INTERNACION_UCE})
DIAS_DEFAULT = 7
DIAS_MAX = 30


def es_origen_internacion(codigo: str | None) -> bool:
    return (codigo or "") in ORIGENES_INTERNACION


def ensayos_recientes_internacion(
    paciente_id: int,
    *,
    dias: int = DIAS_DEFAULT,
    fecha_hasta: date | None = None,
) -> dict[str, Any]:
    """
    Tipos de examen distintos pedidos al paciente en órdenes de internación
    en la ventana ``[fecha_hasta - dias, fecha_hasta]`` (ambos inclusive).

    ``fecha_hasta`` es la fecha del pedido que se está armando
    (p. ej. ``fecha_programada_toma``); por defecto, hoy local.
    Incluye pedidos del mismo día.
    """
    dias = max(1, min(int(dias or DIAS_DEFAULT), DIAS_MAX))
    hasta = fecha_hasta or timezone.localdate()
    desde_fecha = hasta - timedelta(days=dias)

    # Misma ventana en datetime para fecha_solicitud (inicio del día desde / fin del día hasta).
    tz = timezone.get_current_timezone()
    desde_dt = timezone.make_aware(datetime.combine(desde_fecha, time.min), tz)
    hasta_dt_excl = timezone.make_aware(
        datetime.combine(hasta + timedelta(days=1), time.min), tz
    )

    qs = (
        SolicitudExamen.objects.filter(
            paciente_id=paciente_id,
            origen_solicitud__in=ORIGENES_INTERNACION,
        )
        .exclude(estado="CANCELADO")
        .filter(
            Q(fecha_programada_toma__gte=desde_fecha, fecha_programada_toma__lte=hasta)
            | Q(fecha_solicitud__gte=desde_dt, fecha_solicitud__lt=hasta_dt_excl)
        )
        .prefetch_related("tipos_examen")
        .order_by("-fecha_programada_toma", "-fecha_solicitud", "-id")
    )

    por_examen: dict[int, dict[str, Any]] = {}
    for sol in qs:
        if sol.fecha_programada_toma:
            fecha_ref = sol.fecha_programada_toma
        elif sol.fecha_solicitud:
            fecha_ref = timezone.localtime(sol.fecha_solicitud).date()
        else:
            fecha_ref = hasta
        for te in sol.tipos_examen.all():
            prev = por_examen.get(te.id)
            if prev is None or fecha_ref > prev["_fecha_sort"]:
                por_examen[te.id] = {
                    "id": te.id,
                    "codigo": te.codigo,
                    "nombre": te.nombre,
                    "ultima_fecha": fecha_ref.isoformat(),
                    "orden_numero": sol.numero,
                    "_fecha_sort": fecha_ref,
                }

    examenes = sorted(
        (
            {k: v for k, v in row.items() if k != "_fecha_sort"}
            for row in por_examen.values()
        ),
        key=lambda r: (r["ultima_fecha"], r["codigo"]),
        reverse=True,
    )
    return {
        "dias": dias,
        "fecha_hasta": hasta.isoformat(),
        "fecha_desde": desde_fecha.isoformat(),
        "examenes": examenes,
    }
