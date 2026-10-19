"""
Prefetch en memoria para el listado liviano de solicitudes (bandeja LIMS).

Evita N+1 en ``pedido_adicional`` e internación de procedencia cuando se
serializan muchas filas PENDIENTE.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.db.models import Q
from django.utils import timezone


def warm_listado_bandeja_context(solicitudes: list[Any], context: dict) -> None:
    """Rellena caches en ``context`` y atributos en cada solicitud de la página."""
    items = list(solicitudes)
    if not items:
        context["pedido_adicional_by_id"] = {}
        return

    _warm_pedido_adicional(items, context)
    _warm_internaciones_procedencia(items)


def _warm_pedido_adicional(items: list[Any], context: dict) -> None:
    from laboratorio.models import SolicitudExamen
    from laboratorio.solicitud_orden_abierta import (
        ESTADOS_ORDEN_EN_CURSO,
        orden_esperando_recepcion,
        orden_esta_abierta,
    )

    abiertas = [s for s in items if orden_esta_abierta(s)]
    by_id: dict[int, bool] = {s.pk: False for s in items if s.pk is not None}
    if not abiertas:
        context["pedido_adicional_by_id"] = by_id
        return

    paciente_ids = {s.paciente_id for s in abiertas if s.paciente_id}
    if not paciente_ids:
        context["pedido_adicional_by_id"] = by_id
        return

    candidatos = (
        SolicitudExamen.objects.filter(paciente_id__in=paciente_ids)
        .filter(Q(estado__in=ESTADOS_ORDEN_EN_CURSO) | Q(estado="PENDIENTE"))
        .prefetch_related("muestras")
    )
    por_paciente: dict[int, list] = defaultdict(list)
    for c in candidatos:
        por_paciente[c.paciente_id].append(c)

    for s in abiertas:
        blocked = False
        for other in por_paciente.get(s.paciente_id, ()):
            if other.pk == s.pk:
                continue
            if other.estado in ESTADOS_ORDEN_EN_CURSO:
                blocked = True
                break
            if other.estado == "PENDIENTE" and orden_esperando_recepcion(other):
                blocked = True
                break
        by_id[s.pk] = blocked

    context["pedido_adicional_by_id"] = by_id


def _warm_internaciones_procedencia(items: list[Any]) -> None:
    """Una query de internaciones activas para pacientes que la procedencia podría necesitar."""
    from laboratorio.origen_solicitud import (
        _atencion_desde_consulta,
        _atencion_es_guardia,
        es_origen_ambulatorio_externo,
    )

    need_paciente_ids: set[int] = set()
    need_items: list[Any] = []
    for s in items:
        if es_origen_ambulatorio_externo(getattr(s, "origen_solicitud", None)):
            continue
        consulta = getattr(s, "consulta_hc", None)
        if consulta is not None:
            if _atencion_es_guardia(_atencion_desde_consulta(consulta)):
                continue
            turno = getattr(consulta, "turno", None)
            recurso = getattr(turno, "recurso", None) if turno is not None else None
            if recurso is not None:
                continue
        if not s.paciente_id:
            s._procedencia_internacion_prefetch = None
            continue
        need_paciente_ids.add(s.paciente_id)
        need_items.append(s)

    if not need_items:
        return

    try:
        from internacion.models import Internacion
    except Exception:
        for s in need_items:
            s._procedencia_internacion_prefetch = None
        return

    internaciones = (
        Internacion.objects.filter(paciente_id__in=need_paciente_ids, activo=True)
        .select_related("cama__sector")
        .order_by("paciente_id", "-fecha_ingreso")
    )
    por_paciente: dict[int, list] = defaultdict(list)
    for inn in internaciones:
        por_paciente[inn.paciente_id].append(inn)

    for s in need_items:
        fecha_ref = (
            getattr(s, "fecha_solicitud", None)
            or getattr(s, "created_at", None)
            or timezone.now()
        )
        elegida = None
        for inn in por_paciente.get(s.paciente_id, ()):
            ingreso = getattr(inn, "fecha_ingreso", None)
            if ingreso is not None and ingreso <= fecha_ref:
                elegida = inn
                break
        s._procedencia_internacion_prefetch = elegida
