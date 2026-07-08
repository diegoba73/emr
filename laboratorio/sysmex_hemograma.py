"""
Compatibilidad con conversión Sysmex hemograma (delega en entrada_resultados).

Preferir ``laboratorio.entrada_resultados`` con configuración del catálogo TipoExamen.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO
from laboratorio.entrada_resultados import (
    EntradaRule,
    aplicar_valor_ticket_si_corresponde,
    convert_ticket_entry,
    format_informe_entrada,
    get_entrada_rule,
)


class _CodigoTipoExamen:
    """Proxy mínimo para reutilizar reglas legacy por código."""

    def __init__(self, codigo: str):
        self.codigo = codigo
        self.modo_entrada = "ESTANDAR"


SYSMEX_HEMOGRAMA_UNIDADES: dict[str, str] = {
    "LEU": "/mm³",
    "PLAQ": "/mm³",
    "HEMATIES": "mill/mm³",
    "HGB": "g/dL",
    "HTO": "%",
    "RDW": "%",
    "NEUT_CAY": "%",
    "NEUT_SEG": "%",
    "EOS": "%",
    "BAS": "%",
    "LINF": "%",
    "MONO": "%",
}


def _rules_dict() -> dict[str, EntradaRule]:
    out: dict[str, EntradaRule] = {}
    for codigo, row in ENTRADA_DEFAULTS_POR_CODIGO.items():
        modo, dec, mult, fmt = row
        out[codigo] = EntradaRule(int(dec), Decimal(mult), fmt, modo)
    return out


SYSMEX_HEMOGRAMA_RULES = _rules_dict()


def get_sysmex_unidad(codigo: str | None) -> str:
    if not codigo:
        return ""
    return SYSMEX_HEMOGRAMA_UNIDADES.get(codigo.strip().upper(), "")


def is_sysmex_hemograma_codigo(codigo: str | None) -> bool:
    if not codigo:
        return False
    return codigo.strip().upper() in ENTRADA_DEFAULTS_POR_CODIGO


def convert_sysmex_entry(codigo: str, raw_entry: Any) -> dict[str, Any] | None:
    return convert_ticket_entry(_CodigoTipoExamen(codigo), raw_entry)


def format_sysmex_informe(ticket_value: Decimal, display: str) -> str:
    return format_informe_entrada(ticket_value, display)


def aplicar_valor_sysmex_si_corresponde(resultado, tipo_examen, item: dict[str, Any]) -> bool:
    return aplicar_valor_ticket_si_corresponde(resultado, tipo_examen, item)


def get_sysmex_rule(codigo: str) -> EntradaRule | None:
    return get_entrada_rule(_CodigoTipoExamen(codigo))
