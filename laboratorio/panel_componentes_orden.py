"""
Orden de componentes dentro de cada panel (formulario, UI LIMS, informe PDF).

Fuente única: ``catalogo_solicitud_papel.PANELES``.
"""
from __future__ import annotations

from typing import Iterable, Sequence, TypeVar

from laboratorio.catalogo_solicitud_papel import PANELES

T = TypeVar("T")

PANEL_COMPONENTES_BY_CODIGO: dict[str, list[str]] = {
    p["codigo"]: list(p["componentes"]) for p in PANELES
}


def _rank_map(codigos: Sequence[str]) -> dict[str, int]:
    return {codigo: idx for idx, codigo in enumerate(codigos)}


def ordenar_codigos_panel(panel_codigo: str, codigos: Iterable[str]) -> list[str]:
    """Ordena códigos de examen según la definición del panel."""
    canon = PANEL_COMPONENTES_BY_CODIGO.get(panel_codigo)
    if not canon:
        return sorted(set(codigos))
    rank = _rank_map(canon)
    uniq = list(dict.fromkeys(codigos))
    return sorted(uniq, key=lambda c: (rank.get(c, 10_000), c))


def ordenar_ids_por_panel(
    panel_codigo: str,
    pares_id_codigo: Iterable[tuple[int, str]],
) -> list[int]:
    """Ordena ids de TipoExamen según el panel."""
    items = list(pares_id_codigo)
    if not items:
        return []
    canon = PANEL_COMPONENTES_BY_CODIGO.get(panel_codigo)
    if not canon:
        return sorted(pk for pk, _ in items)
    rank = _rank_map(canon)
    items.sort(key=lambda pair: (rank.get(pair[1], 10_000), pair[1]))
    return [pk for pk, _ in items]


def ordenar_queryset_panel(panel) -> list:
    """Ordena tipos_examen de un PanelExamen."""
    examenes = list(panel.tipos_examen.all())
    if not examenes:
        return []
    pares = [(te.id, te.codigo) for te in examenes]
    ids = ordenar_ids_por_panel(panel.codigo, pares)
    by_id = {te.id: te for te in examenes}
    return [by_id[pk] for pk in ids if pk in by_id]


def ordenar_resultados_por_panel(panel_codigo: str, resultados: Iterable[T]) -> list[T]:
    """Ordena resultados (objeto con tipo_examen_id o tipo_examen.codigo)."""
    rows = list(resultados)
    if not rows:
        return rows

    def _codigo(res) -> str:
        te = getattr(res, "tipo_examen", None)
        if te is not None and hasattr(te, "codigo"):
            return str(te.codigo or "")
        if hasattr(res, "tipo_examen_codigo"):
            return str(res.tipo_examen_codigo or "")
        return ""

    def _tipo_id(res) -> int:
        te = getattr(res, "tipo_examen", None)
        if hasattr(te, "id"):
            return int(te.id)
        if hasattr(res, "tipo_examen_id"):
            return int(res.tipo_examen_id)
        if isinstance(te, int):
            return int(te)
        return 0

    canon = PANEL_COMPONENTES_BY_CODIGO.get(panel_codigo)
    if not canon:
        return sorted(rows, key=lambda r: (_codigo(r), _tipo_id(r)))

    rank = _rank_map(canon)
    return sorted(rows, key=lambda r: (rank.get(_codigo(r), 10_000), _codigo(r), _tipo_id(r)))
