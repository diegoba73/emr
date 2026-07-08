"""
Conversión de valores de entrada según configuración del catálogo TipoExamen.

Modos:
- ESTANDAR: texto/número directo.
- TICKET_ENTERO: entero del ticket analizador sin punto decimal.
- FORMULA_PORCENTAJE: % directo (fórmula leucocitaria, suma 100).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ValidationError

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO

VALOR_NUMERICO_QUANT = Decimal("0.0001")


def quantize_valor_numerico(value: Decimal) -> Decimal:
    """Alinea con ResultadoExamen.valor_numerico (max 4 decimales)."""
    return value.quantize(VALOR_NUMERICO_QUANT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class EntradaRule:
    ticket_decimals: int
    clinical_multiplier: Decimal
    display: str
    modo: str


def _legacy_rule_from_codigo(codigo: str | None) -> EntradaRule | None:
    if not codigo:
        return None
    row = ENTRADA_DEFAULTS_POR_CODIGO.get(codigo.strip().upper())
    if not row:
        return None
    modo, dec, mult, fmt = row
    return EntradaRule(int(dec), Decimal(mult), fmt, modo)


def get_entrada_rule(tipo_examen) -> EntradaRule | None:
    """Regla de conversión desde TipoExamen; fallback legacy por código."""
    modo = getattr(tipo_examen, "modo_entrada", None) or "ESTANDAR"
    if modo == "ESTANDAR":
        return _legacy_rule_from_codigo(getattr(tipo_examen, "codigo", None))

    if modo in ("TICKET_ENTERO", "FORMULA_PORCENTAJE"):
        fmt = (getattr(tipo_examen, "formato_informe_entrada", None) or "").strip()
        if not fmt:
            return _legacy_rule_from_codigo(getattr(tipo_examen, "codigo", None))
        return EntradaRule(
            int(getattr(tipo_examen, "ticket_decimales", 0) or 0),
            Decimal(str(getattr(tipo_examen, "multiplicador_clinico", 1) or 1)),
            fmt,
            modo,
        )
    return None


def uses_ticket_entry(tipo_examen) -> bool:
    modo = getattr(tipo_examen, "modo_entrada", None) or "ESTANDAR"
    if modo in ("TICKET_ENTERO", "FORMULA_PORCENTAJE"):
        return True
    return _legacy_rule_from_codigo(getattr(tipo_examen, "codigo", None)) is not None


def is_formula_percent(tipo_examen) -> bool:
    modo = getattr(tipo_examen, "modo_entrada", None) or "ESTANDAR"
    if modo == "FORMULA_PORCENTAJE":
        return True
    codigo = (getattr(tipo_examen, "codigo", None) or "").strip().upper()
    legacy = ENTRADA_DEFAULTS_POR_CODIGO.get(codigo)
    return legacy is not None and legacy[0] == "FORMULA_PORCENTAJE" and modo == "ESTANDAR"


def _parse_positive_int(raw: Any) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text.isdigit():
        return None
    value = int(text)
    return value if value >= 0 else None


def _format_decimal1(value: Decimal) -> str:
    q = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{q:.1f}"


def _format_absolute_int(value: Decimal) -> str:
    n = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return str(n)


def _format_absolute_millions(ticket_value: Decimal) -> str:
    absolute = int((ticket_value * Decimal("1000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{absolute:,}".replace(",", ".")


def format_informe_entrada(ticket_value: Decimal, display: str) -> str:
    if display == "decimal1":
        return _format_decimal1(ticket_value)
    if display == "absolute_int":
        return _format_absolute_int(ticket_value * Decimal("1000"))
    if display == "absolute_millions":
        return _format_absolute_millions(ticket_value)
    if display == "integer":
        return str(int(ticket_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
    return str(ticket_value)


def convert_ticket_entry(tipo_examen, raw_entry: Any) -> dict[str, Any] | None:
    """Convierte entero del ticket a valor numérico clínico y texto de informe."""
    rule = get_entrada_rule(tipo_examen)
    if not rule:
        return None
    entry = _parse_positive_int(raw_entry)
    if entry is None:
        return None

    ticket_value = Decimal(entry) / (Decimal(10) ** rule.ticket_decimals)
    valor_numerico = quantize_valor_numerico(ticket_value * rule.clinical_multiplier)
    valor_informe = format_informe_entrada(ticket_value, rule.display)
    return {
        "entry": entry,
        "ticket_value": ticket_value,
        "valor_numerico": valor_numerico,
        "valor_informe": valor_informe,
    }


def entry_from_stored(tipo_examen, valor_numerico: Any) -> str:
    rule = get_entrada_rule(tipo_examen)
    if not rule or valor_numerico in (None, ""):
        return ""
    try:
        numeric = Decimal(str(valor_numerico))
    except Exception:
        return ""
    ticket_value = numeric / rule.clinical_multiplier
    entry = int(
        (ticket_value * (Decimal(10) ** rule.ticket_decimals)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    return str(entry) if entry > 0 else ""


def aplicar_valor_ticket_si_corresponde(resultado, tipo_examen, item: dict[str, Any]) -> bool:
    """
    Si el ítem trae ``valor_sysmex`` y el examen usa entrada ticket,
    reemplaza valor/valor_numerico antes de la carga estructurada.
    """
    raw = item.get("valor_sysmex")
    if raw in (None, "") or not uses_ticket_entry(tipo_examen):
        return False

    conv = convert_ticket_entry(tipo_examen, raw)
    if conv is None:
        codigo = (getattr(tipo_examen, "codigo", None) or "").strip()
        nombre = (getattr(tipo_examen, "nombre", None) or codigo or "examen").strip()
        raise ValidationError(
            f"Valor de ticket inválido para {nombre}. Ingrese solo dígitos, sin punto decimal."
        )

    item["valor_obtenido"] = conv["valor_informe"]
    item["valor_numerico"] = quantize_valor_numerico(conv["valor_numerico"])
    if "valor" in item:
        item["valor"] = conv["valor_informe"]
    return True
