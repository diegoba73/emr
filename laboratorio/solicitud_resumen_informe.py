"""
Resumen de paneles/resultados para vistas nested (HC, revista) con el mismo
orden de grupos que el informe PDF (`orden_grupos_informe` + default papel).
"""
from __future__ import annotations

from typing import Any

from laboratorio.panel_componentes_orden import ordenar_ids_por_panel


def paneles_resumen_solicitud(solicitud) -> list[dict[str, Any]]:
    """Misma forma que SolicitudExamenSerializer.get_paneles_resumen."""
    out: list[dict[str, Any]] = []
    for p in solicitud.paneles.all():
        pares = list(p.tipos_examen.values_list("id", "codigo"))
        out.append(
            {
                "id": p.id,
                "codigo": p.codigo,
                "nombre": p.nombre,
                "tipos_examen_ids": ordenar_ids_por_panel(p.codigo, pares),
            }
        )
    return out


def _muestra_codigo_tipo(tipo) -> str | None:
    if tipo is None:
        return None
    tm = getattr(tipo, "tipo_muestra_requerida", None)
    if tm is None:
        return None
    codigo = getattr(tm, "codigo", None)
    return str(codigo) if codigo else None


def resultado_resumen_informe(res) -> dict[str, Any]:
    """Campos mínimos para groupResultadosPorPanel / ResultadosOrdenLista."""
    tipo = getattr(res, "tipo_examen", None)
    valor = (res.valor_obtenido or "").strip()
    unidad = res.unidad or ""
    if tipo and not unidad:
        unidad = getattr(tipo, "unidad", None) or ""
    return {
        "id": res.pk,
        "tipo_examen": tipo.pk if tipo else None,
        "tipo_examen_nombre": tipo.nombre if tipo else None,
        "tipo_examen_codigo": (tipo.codigo if tipo else None) or None,
        "tipo_examen_muestra_codigo": _muestra_codigo_tipo(tipo),
        "valor_obtenido": res.valor_obtenido,
        "unidad": unidad,
        "estado": "CARGADO" if valor else "PENDIENTE",
        "es_patologico": bool(res.es_patologico),
        # Compat revista (nombres legacy).
        "examen": tipo.nombre if tipo else None,
        "valor": res.valor_obtenido or "",
    }


PREFETCH_SOLICITUD_RESUMEN_INFORME = (
    "tipos_examen",
    "paneles__tipos_examen",
    "resultados__tipo_examen__tipo_muestra_requerida",
)
