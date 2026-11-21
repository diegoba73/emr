"""
Acompañamientos clínicos al armar pedidos LIMS.

Reglas que no son insumos de un calculado ni componentes de un panel, sino
prácticas que deben viajar juntas (p. ej. coagulograma + plaquetas,
EAB sin hemograma + hematocrito).
"""
from __future__ import annotations

from typing import Iterable

PANEL_COAGULOGRAMA = "PAN_COAG"
PANEL_HEMOGRAMA = "PAN_HEMO"
PANELES_EAB = frozenset({"PAN_EAB_ART", "PAN_EAB_VEN"})
# Coagulograma sin hemograma → plaquetas (recuento acompañante).
EXAMENES_ACOMPANAN_COAG_SIN_HEMO: tuple[str, ...] = ("PLAQ",)
# EAB (gases) sin hemograma → hematocrito.
EXAMENES_ACOMPANAN_EAB_SIN_HEMO: tuple[str, ...] = ("HTO",)


def codigos_acompanamiento_pedido(
    *,
    codigos_examen: Iterable[str],
    codigos_panel: Iterable[str],
) -> list[str]:
    """
    Códigos de examen a agregar según paneles ya elegidos.

    - ``PAN_COAG`` sin ``PAN_HEMO`` → ``PLAQ`` si falta.
    - EAB art/ven sin ``PAN_HEMO`` → ``HTO`` si falta.
    """
    exams = {(c or "").strip().upper() for c in (codigos_examen or []) if c}
    panels = {(c or "").strip().upper() for c in (codigos_panel or []) if c}
    out: list[str] = []
    if PANEL_COAGULOGRAMA in panels and PANEL_HEMOGRAMA not in panels:
        for code in EXAMENES_ACOMPANAN_COAG_SIN_HEMO:
            if code not in exams:
                out.append(code)
    if panels & PANELES_EAB and PANEL_HEMOGRAMA not in panels:
        for code in EXAMENES_ACOMPANAN_EAB_SIN_HEMO:
            if code not in exams:
                out.append(code)
    return out
