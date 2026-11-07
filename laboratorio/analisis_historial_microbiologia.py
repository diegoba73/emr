"""
Historial de microbiología por paciente + tipo de cultivo.

Espejo de ``historial_analitos_solicitud`` (clínico): previos informados del
mismo «parámetro» (tipo de cultivo), sin filtrar por microorganismo — el
organismo puede cambiar entre episodios.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db.models import Prefetch
from django.utils import timezone

from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    EstudioMicrobiologia,
    LecturaCultivo,
)

# Estudios ya cerrados/informados (análogo a FINALIZADO / INFORMADO_PARCIAL clínico).
ESTADOS_HISTORIAL_MICRO = frozenset({"VALIDADO", "INFORMADO"})

CRECIMIENTOS_CON_DESARROLLO = frozenset(
    {"ESCASO", "MODERADO", "ABUNDANTE", "MIXTO"}
)


def _fecha_a_json(value: datetime | None) -> str | None:
    if value is None:
        return None
    if timezone.is_aware(value):
        return value.isoformat()
    return value.isoformat()


def clasificar_desarrollo(estudio: EstudioMicrobiologia) -> str:
    """
    ``SIN_DESARROLLO`` | ``CON_DESARROLLO`` | ``SIN_LECTURA``.

    No mira el microorganismo actual: solo lecturas/aislados del episodio.
    """
    lecturas = list(getattr(estudio, "_prefetched_objects_cache", {}).get("lecturas") or [])
    if not lecturas and hasattr(estudio, "lecturas"):
        lecturas = list(estudio.lecturas.all())

    crecimientos = [(l.crecimiento or "").strip().upper() for l in lecturas]
    if any(c in CRECIMIENTOS_CON_DESARROLLO for c in crecimientos):
        return "CON_DESARROLLO"
    if crecimientos and all(c == "SIN_DESARROLLO" for c in crecimientos):
        return "SIN_DESARROLLO"

    aislados = list(getattr(estudio, "_prefetched_objects_cache", {}).get("aislados") or [])
    if not aislados and hasattr(estudio, "aislados"):
        aislados = list(estudio.aislados.all())
    for a in aislados:
        if (a.estado or "").upper() == "DESCARTADO":
            continue
        if a.microorganismo_id:
            return "CON_DESARROLLO"

    if not lecturas:
        return "SIN_LECTURA"
    return "SIN_LECTURA"


def microorganismos_del_estudio(estudio: EstudioMicrobiologia) -> list[dict[str, Any]]:
    """
    Cualquier microorganismo aislado en el episodio (no DESCARTADO).

    No se filtra por el organismo del estudio actual.
    """
    aislados = list(getattr(estudio, "_prefetched_objects_cache", {}).get("aislados") or [])
    if not aislados and hasattr(estudio, "aislados"):
        aislados = list(
            estudio.aislados.select_related("microorganismo").all()
        )

    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for a in aislados:
        if (a.estado or "").upper() == "DESCARTADO":
            continue
        mo = a.microorganismo
        if mo is None:
            continue
        if mo.pk in seen:
            continue
        seen.add(mo.pk)
        out.append(
            {
                "microorganismo_id": mo.pk,
                "codigo": (getattr(mo, "codigo", None) or "").strip() or None,
                "nombre": (mo.nombre or "").strip() or f"#{mo.pk}",
                "aislado_id": a.pk,
                "aislado_estado": a.estado,
            }
        )
    return out


def label_desarrollo(codigo: str) -> str:
    return {
        "CON_DESARROLLO": "Con desarrollo",
        "SIN_DESARROLLO": "Sin desarrollo",
        "SIN_LECTURA": "Sin lectura",
    }.get(codigo, codigo)


def serializar_episodio_previo(estudio: EstudioMicrobiologia) -> dict[str, Any]:
    desarrollo = clasificar_desarrollo(estudio)
    organismos = microorganismos_del_estudio(estudio)
    fecha = getattr(estudio, "fecha_inicio", None) or estudio.created_at
    return {
        "estudio_id": estudio.pk,
        "estudio_numero": estudio.numero,
        "estado": estudio.estado,
        "fecha": _fecha_a_json(fecha),
        "desarrollo": desarrollo,
        "desarrollo_display": label_desarrollo(desarrollo),
        "microorganismos": organismos,
        "tipo_cultivo_id": estudio.tipo_cultivo_id,
        "tipo_cultivo_nombre": (
            estudio.tipo_cultivo.nombre
            if estudio.tipo_cultivo_id and estudio.tipo_cultivo
            else None
        )
        or (estudio.tipo_estudio or None),
    }


def buscar_estudios_historicos_mismo_cultivo(
    *,
    paciente_id: int,
    tipo_cultivo_id: int | None,
    tipo_estudio: str | None,
    excluir_estudio_id: int,
    antes_de: datetime | None = None,
    limit: int = 10,
) -> list[EstudioMicrobiologia]:
    """
    Episodios previos del mismo tipo de cultivo (parámetro), cualquier organismo.
    """
    if limit < 1:
        return []

    qs = EstudioMicrobiologia.objects.filter(
        paciente_id=paciente_id,
        estado__in=ESTADOS_HISTORIAL_MICRO,
    ).exclude(pk=excluir_estudio_id)

    if tipo_cultivo_id:
        qs = qs.filter(tipo_cultivo_id=tipo_cultivo_id)
    else:
        codigo = (tipo_estudio or "").strip().upper()
        if not codigo:
            return []
        qs = qs.filter(tipo_estudio__iexact=codigo)

    if antes_de is not None:
        qs = qs.filter(created_at__lt=antes_de)

    qs = (
        qs.select_related("tipo_cultivo")
        .prefetch_related(
            Prefetch(
                "lecturas",
                queryset=LecturaCultivo.objects.order_by("-fecha_lectura", "-id"),
            ),
            Prefetch(
                "aislados",
                queryset=AisladoMicrobiologico.objects.select_related(
                    "microorganismo"
                ).order_by("-created_at", "-id"),
            ),
        )
        .order_by("-created_at", "-id")
    )
    return list(qs[:limit])


def historial_cultivo_estudio(
    estudio: EstudioMicrobiologia,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Previos del mismo cultivo para el paciente (UI de estudio microbiología).

    No filtra por microorganismo del episodio actual.
    """
    limit = max(1, min(int(limit or 10), 50))
    previos = buscar_estudios_historicos_mismo_cultivo(
        paciente_id=estudio.paciente_id,
        tipo_cultivo_id=estudio.tipo_cultivo_id,
        tipo_estudio=estudio.tipo_estudio,
        excluir_estudio_id=estudio.pk,
        antes_de=estudio.created_at,
        limit=limit,
    )
    return {
        "estudio_id": estudio.pk,
        "paciente_id": estudio.paciente_id,
        "tipo_cultivo_id": estudio.tipo_cultivo_id,
        "tipo_cultivo_codigo": (
            (estudio.tipo_cultivo.codigo if estudio.tipo_cultivo_id else None)
            or (estudio.tipo_estudio or None)
        ),
        "tipo_cultivo_nombre": (
            estudio.tipo_cultivo.nombre
            if estudio.tipo_cultivo_id and estudio.tipo_cultivo
            else None
        )
        or (estudio.tipo_estudio or None),
        "limit": limit,
        "previos": [serializar_episodio_previo(e) for e in previos],
    }
