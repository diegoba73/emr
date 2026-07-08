"""
Defaults de modo de entrada de resultados por código de examen (seed / migración).

Usado al cargar el catálogo de solicitud en papel y al migrar exámenes existentes.
"""
from __future__ import annotations

from decimal import Decimal

# modo_entrada, ticket_decimales, multiplicador_clinico, formato_informe_entrada
EntradaDefault = tuple[str, int, str, str]

ENTRADA_DEFAULTS_POR_CODIGO: dict[str, EntradaDefault] = {
    "LEU": ("TICKET_ENTERO", 1, "1000", "absolute_int"),
    "PLAQ": ("TICKET_ENTERO", 0, "1000", "absolute_int"),
    "HEMATIES": ("TICKET_ENTERO", 2, "1", "absolute_millions"),
    "HGB": ("TICKET_ENTERO", 1, "1", "decimal1"),
    "HTO": ("TICKET_ENTERO", 1, "1", "decimal1"),
    "RDW": ("TICKET_ENTERO", 1, "1", "decimal1"),
    "NEUT_CAY": ("FORMULA_PORCENTAJE", 0, "1", "integer"),
    "NEUT_SEG": ("FORMULA_PORCENTAJE", 0, "1", "integer"),
    "EOS": ("FORMULA_PORCENTAJE", 0, "1", "integer"),
    "BAS": ("FORMULA_PORCENTAJE", 0, "1", "integer"),
    "LINF": ("FORMULA_PORCENTAJE", 0, "1", "integer"),
    "MONO": ("FORMULA_PORCENTAJE", 0, "1", "integer"),
}


def entrada_defaults_dict(codigo: str) -> dict:
    row = ENTRADA_DEFAULTS_POR_CODIGO.get((codigo or "").strip().upper())
    if not row:
        return {}
    modo, dec, mult, fmt = row
    return {
        "modo_entrada": modo,
        "ticket_decimales": dec,
        "multiplicador_clinico": Decimal(mult),
        "formato_informe_entrada": fmt,
    }
