"""
Orden de grupos (paneles y exámenes sueltos) en el informe PDF y la UI LIMS.

Reglas por defecto:
- Hemograma (PAN_HEMO) primero si está pedido.
- Paneles y exámenes de orina al final.
- El resto en el medio (por nombre).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, TypeVar

from laboratorio.panel_componentes_orden import ordenar_resultados_por_panel

T = TypeVar("T")

PANEL_HEMOGRAMA = "PAN_HEMO"
PANELES_ORINA = frozenset(
    {
        "PAN_ORI",
        "PAN_IONO_U",
        "PAN_IONO_U24",
        "PAN_MALB_AZ",
        "PAN_MALB24",
    }
)
CODIGOS_ORINA_SUELTOS = frozenset({"PROT_U_24", "PROT_U_AZ"})


def grupo_key_panel(panel_id: int) -> str:
    return f"panel-{panel_id}"


def grupo_key_resultado(resultado_id: int) -> str:
    return f"resultado-{resultado_id}"


@dataclass
class GrupoInformeSpec:
    key: str
    titulo: str
    panel_codigo: str | None = None
    resultados: list = field(default_factory=list)


def _es_orina_panel(codigo: str | None) -> bool:
    return bool(codigo and codigo in PANELES_ORINA)


def _codigo_tipo_examen(res) -> str:
    te = getattr(res, "tipo_examen", None)
    if te is not None and hasattr(te, "codigo"):
        return str(te.codigo or "").strip().upper()
    if hasattr(res, "tipo_examen_codigo"):
        return str(res.tipo_examen_codigo or "").strip().upper()
    return ""


def _es_orina_resultado(res) -> bool:
    codigo = _codigo_tipo_examen(res)
    if codigo in CODIGOS_ORINA_SUELTOS:
        return True
    te = getattr(res, "tipo_examen", None)
    tm = getattr(te, "tipo_muestra_requerida", None) if te else None
    if tm and (getattr(tm, "codigo", None) or "").strip().upper() == "ORINA":
        return True
    return False


def prioridad_grupo_default(grupo: GrupoInformeSpec) -> tuple[int, str]:
    if grupo.panel_codigo == PANEL_HEMOGRAMA:
        return (0, grupo.titulo)
    if _es_orina_panel(grupo.panel_codigo):
        return (3, grupo.titulo)
    if grupo.key.startswith("resultado-") and grupo.resultados and _es_orina_resultado(grupo.resultados[0]):
        return (3, grupo.titulo)
    if grupo.panel_codigo:
        return (1, grupo.titulo)
    return (2, grupo.titulo)


def construir_grupos_informe(solicitud, resultados: Iterable) -> list[GrupoInformeSpec]:
    """Agrupa resultados: un bloque por panel y un bloque por examen suelto."""
    paneles = list(solicitud.paneles.prefetch_related("tipos_examen").all())
    asignados: set[int] = set()
    grupos: list[GrupoInformeSpec] = []

    for panel in paneles:
        ids_panel = {te.id for te in panel.tipos_examen.all()}
        rows = ordenar_resultados_por_panel(
            panel.codigo,
            [r for r in resultados if r.tipo_examen_id in ids_panel],
        )
        for r in rows:
            asignados.add(r.id)
        if rows:
            grupos.append(
                GrupoInformeSpec(
                    key=grupo_key_panel(panel.pk),
                    titulo=panel.nombre.upper(),
                    panel_codigo=panel.codigo,
                    resultados=rows,
                )
            )

    otros = [r for r in resultados if r.id not in asignados]
    for r in otros:
        te = getattr(r, "tipo_examen", None)
        titulo = (getattr(te, "nombre", None) or "EXAMEN").upper()
        grupos.append(
            GrupoInformeSpec(
                key=grupo_key_resultado(r.id),
                titulo=titulo,
                resultados=[r],
            )
        )

    return grupos


def ordenar_grupos_por_defecto(grupos: list[GrupoInformeSpec]) -> list[GrupoInformeSpec]:
    return sorted(grupos, key=lambda g: (*prioridad_grupo_default(g), g.key))


def aplicar_orden_grupos(
    grupos: list[GrupoInformeSpec],
    orden_custom: list[str] | None,
) -> list[GrupoInformeSpec]:
    if not orden_custom:
        return ordenar_grupos_por_defecto(grupos)

    by_key = {g.key: g for g in grupos}
    ordered: list[GrupoInformeSpec] = []
    seen: set[str] = set()
    for key in orden_custom:
        if key in by_key and key not in seen:
            ordered.append(by_key[key])
            seen.add(key)

    rest = [g for g in grupos if g.key not in seen]
    if rest:
        ordered.extend(ordenar_grupos_por_defecto(rest))
    return ordered


def claves_grupos_validas(solicitud, resultados: Iterable) -> set[str]:
    return {g.key for g in construir_grupos_informe(solicitud, resultados)}


def validar_orden_grupos(orden: list, claves_validas: set[str]) -> list[str] | None:
    if not isinstance(orden, list):
        return None
    out: list[str] = []
    seen: set[str] = set()
    for item in orden:
        if not isinstance(item, str):
            return None
        if item not in claves_validas or item in seen:
            continue
        out.append(item)
        seen.add(item)
    return out
