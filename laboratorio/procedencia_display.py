"""
Resolución de procedencia clínica de una orden LIMS (recurso ambulatorio vs internación).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from laboratorio.models import SolicitudExamen


def resolver_procedencia_solicitud(solicitud: SolicitudExamen) -> dict[str, Any]:
    """
    Devuelve tipo y texto legible de dónde proviene la solicitud de muestra.

    Prioridad:
    0. Origen ambulatorio externo (receta presentada en CEHTA/ICPL)
    1. Consulta HC → turno → recurso (ambulatorio interno)
    2. Internación activa del paciente a la fecha de la orden
    3. Fallback según origen_solicitud
    """
    from laboratorio.origen_solicitud import (
        es_origen_ambulatorio_externo,
        procedencia_display_externo,
    )

    if es_origen_ambulatorio_externo(getattr(solicitud, "origen_solicitud", None)):
        display = procedencia_display_externo(solicitud)
        return {
            "procedencia_tipo": None,
            "procedencia_display": display or "Receta externa",
        }

    consulta = getattr(solicitud, "consulta_hc", None)
    if consulta is not None:
        turno = getattr(consulta, "turno", None)
        recurso = getattr(turno, "recurso", None) if turno is not None else None
        if recurso is not None:
            ubicacion = recurso.get_ubicacion_display() if recurso.ubicacion else ""
            tipo_recurso = recurso.get_tipo_recurso_display() if recurso.tipo_recurso else ""
            partes = [p for p in (tipo_recurso, recurso.nombre, ubicacion) if p]
            return {
                "procedencia_tipo": "RECURSO",
                "procedencia_display": " — ".join(partes) if partes else recurso.nombre,
                "procedencia_recurso_id": recurso.pk,
                "procedencia_recurso_nombre": recurso.nombre,
                "procedencia_ubicacion": ubicacion or None,
            }

    try:
        from internacion.models import Internacion

        internacion = (
            Internacion.objects.filter(
                paciente_id=solicitud.paciente_id,
                activo=True,
                fecha_ingreso__lte=solicitud.fecha_solicitud,
            )
            .select_related("cama__sector")
            .order_by("-fecha_ingreso")
            .first()
        )
        if internacion is not None:
            sector = internacion.cama.sector.nombre if internacion.cama_id else ""
            cama = internacion.cama.nombre if internacion.cama_id else ""
            detalle = f"{sector} — {cama}".strip(" —")
            return {
                "procedencia_tipo": "INTERNACION",
                "procedencia_display": f"Internación — {detalle}" if detalle else "Internación",
                "procedencia_sector": sector or None,
                "procedencia_cama": cama or None,
            }
    except Exception:
        pass

    origen = getattr(solicitud, "origen_solicitud", "") or ""
    from laboratorio.origen_solicitud import label_origen_solicitud

    return {
        "procedencia_tipo": None,
        "procedencia_display": label_origen_solicitud(origen) if origen else "—",
    }
