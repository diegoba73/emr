"""
Parseo de valores con operador de desigualdad (<, >, ≤, ≥).

Política clínica (asistencial):
- El texto informado se conserva tal cual en ``valor_obtenido`` (p. ej. ``"<0.1"``).
- El número de trabajo para rangos / derivados / gráficas es el **límite** (0.1).
- No inventa mitad de LOD ni reescribe resultados ya persistidos (eso lo hace la carga).
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, NamedTuple


_OPS = (
    ("<=", "<="),
    (">=", ">="),
    ("≤", "<="),
    ("≥", ">="),
    ("<", "<"),
    (">", ">"),
)

# "<0.1", "< 0,1", "<=20", "≥ 3.5"
_RE = re.compile(
    r"^\s*(<=|>=|≤|≥|<|>)\s*([+-]?\d+(?:[.,]\d+)?)\s*$",
    re.UNICODE,
)


class ValorConOperador(NamedTuple):
    operador: str | None  # '<', '>', '<=', '>=' o None si es número puro
    numero: Decimal | None
    texto: str


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def parse_valor_con_operador(raw: Any) -> ValorConOperador:
    """
    Interpreta un valor de resultado.

    - ``"<0.1"`` → operador ``<``, número ``0.1``
    - ``"12.5"`` / ``12.5`` → sin operador, número ``12.5``
    - ``"Positivo"`` → sin número
    """
    if raw is None:
        return ValorConOperador(None, None, "")
    if isinstance(raw, (int, float, Decimal)) and not isinstance(raw, bool):
        try:
            return ValorConOperador(None, Decimal(str(raw)), str(raw))
        except (InvalidOperation, ValueError):
            return ValorConOperador(None, None, str(raw))

    texto = str(raw).strip()
    if not texto:
        return ValorConOperador(None, None, "")

    m = _RE.match(texto)
    if m:
        op_raw, num_raw = m.group(1), m.group(2)
        op = dict(_OPS).get(op_raw, op_raw)
        num = _to_decimal(num_raw)
        return ValorConOperador(op, num, texto)

    num = _to_decimal(texto)
    if num is not None:
        return ValorConOperador(None, num, texto)
    return ValorConOperador(None, None, texto)


def numero_para_calculo(raw: Any) -> Decimal | None:
    """Número usable en derivados / rangos / series (límite si hay operador)."""
    return parse_valor_con_operador(raw).numero
