"""
Acompañamientos clínicos al armar pedidos LIMS.

Reglas que no son insumos de un calculado ni componentes de un panel, sino
prácticas que deben viajar juntas (p. ej. coagulograma + plaquetas).
"""
from __future__ import annotations

from typing import Iterable

PANEL_COAGULOGRAMA = "PAN_COAG"
PANEL_HEMOGRAMA = "PAN_HEMO"
# Coagulograma sin hemograma → plaquetas (recuento acompañante).
EXAMENES_ACOMPANAN_COAG_SIN_HEMO: tuple[str, ...] = ("PLAQ",)


def codigos_acompanamiento_pedido(
    *,
    codigos_examen: Iterable[str],
    codigos_panel: Iterable[str],
) -> list[str]:
    """
    Códigos de examen a agregar según paneles ya elegidos.

    Hoy: si hay ``PAN_COAG`` y no ``PAN_HEMO``, incluir ``PLAQ`` si falta.
    """
    exams = {(c or "").strip().upper() for c in (codigos_examen or []) if c}
    panels = {(c or "").strip().upper() for c in (codigos_panel or []) if c}
    out: list[str] = []
    if PANEL_COAGULOGRAMA in panels and PANEL_HEMOGRAMA not in panels:
        for code in EXAMENES_ACOMPANAN_COAG_SIN_HEMO:
            if code not in exams:
                out.append(code)
    return out
