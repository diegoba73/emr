"""Detección de candidatos a paciente duplicado (prevención al alta).

No fusiona fichas: solo busca coincidencias exactas por DNI o por
identidad demográfica (nombre + apellido + fecha de nacimiento).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from django.db.models import QuerySet

from .models import Paciente
from .texto import normalizar_texto_paciente

MATCH_DNI = "dni"
MATCH_IDENTIDAD = "identidad"


def _parse_fecha(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def candidatos_por_dni(
    queryset: QuerySet[Paciente],
    dni: str | None,
    *,
    exclude_id: int | None = None,
) -> QuerySet[Paciente]:
    text = str(dni).strip() if dni is not None else ""
    if not text:
        return queryset.none()
    qs = queryset.filter(dni__iexact=text)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    return qs.order_by("id")


def candidatos_por_identidad(
    queryset: QuerySet[Paciente],
    *,
    nombre: str | None,
    apellido: str | None,
    fecha_nacimiento: Any,
    exclude_id: int | None = None,
) -> QuerySet[Paciente]:
    nombre_n = normalizar_texto_paciente(nombre) or ""
    apellido_n = normalizar_texto_paciente(apellido) or ""
    fnac = _parse_fecha(fecha_nacimiento)
    if not nombre_n or not apellido_n or fnac is None:
        return queryset.none()
    qs = queryset.filter(
        nombre__iexact=nombre_n,
        apellido__iexact=apellido_n,
        fecha_nacimiento=fnac,
    )
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    return qs.order_by("id")


def clasificar_candidatos(
    queryset: QuerySet[Paciente],
    *,
    dni: str | None = None,
    nombre: str | None = None,
    apellido: str | None = None,
    fecha_nacimiento: Any = None,
    exclude_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Devuelve lista de dicts ``{match, paciente}`` sin duplicar el mismo id.

    Prioridad: match DNI exacto sobre identidad demográfica.
    """
    by_id: dict[int, dict[str, Any]] = {}

    for p in candidatos_por_dni(queryset, dni, exclude_id=exclude_id)[:limit]:
        by_id[p.pk] = {"match": MATCH_DNI, "paciente": p}

    for p in candidatos_por_identidad(
        queryset,
        nombre=nombre,
        apellido=apellido,
        fecha_nacimiento=fecha_nacimiento,
        exclude_id=exclude_id,
    )[:limit]:
        if p.pk not in by_id:
            by_id[p.pk] = {"match": MATCH_IDENTIDAD, "paciente": p}

    ordered = sorted(
        by_id.values(),
        key=lambda item: (0 if item["match"] == MATCH_DNI else 1, item["paciente"].pk),
    )
    return ordered[:limit]


def tiene_bloqueo_dni(candidatos: Iterable[dict[str, Any]]) -> bool:
    return any(item.get("match") == MATCH_DNI for item in candidatos)
