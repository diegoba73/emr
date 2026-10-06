"""
Proteinograma electroforético: % derivados desde fracciones en g/dL.

Carga clínica: PROT_T + ELP_* en g/dL; el informe calcula
``% = (g/dL_fracción / PROT_T) × 100``.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

PANEL_ELP = "PAN_ELP"

CODIGO_PROT_T = "PROT_T"
CODIGO_ELP_AG = "ELP_AG"
CODIGO_ELP_CONC = "ELP_CONC"

# Orden de fracciones para tabla e informe (excluye totales, A/G y conclusión).
CODIGOS_ELP_FRACCIONES: tuple[str, ...] = (
    "ELP_ALB",
    "ELP_A1",
    "ELP_A2",
    "ELP_B1",
    "ELP_B2",
    "ELP_GAM",
)

# Etiquetas de informe (mayúsculas clínicas).
ETIQUETAS_ELP: dict[str, str] = {
    CODIGO_PROT_T: "PROTEÍNAS TOTALES",
    "ELP_ALB": "ALBÚMINA",
    "ELP_A1": "ALFA 1 GLOBULINAS",
    "ELP_A2": "ALFA 2 GLOBULINAS",
    "ELP_B1": "BETA 1 GLOBULINAS",
    "ELP_B2": "BETA 2 GLOBULINAS",
    "ELP_GAM": "GAMMA GLOBULINAS",
    CODIGO_ELP_AG: "RELACIÓN ALBÚMINA/GLOBULINA",
    CODIGO_ELP_CONC: "OBSERVACIONES",
}

def _as_decimal(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and (raw != raw):  # NaN
            return None
        return Decimal(str(raw))
    text = str(raw).strip().replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def porcentaje_fraccion(gdl_fraccion: Any, prot_t: Any) -> Decimal | None:
    """% = g/dL_fracción / PROT_T × 100 (1 decimal)."""
    frac = _as_decimal(gdl_fraccion)
    total = _as_decimal(prot_t)
    if frac is None or total is None or total == 0:
        return None
    pct = (frac / total) * Decimal("100")
    return pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def porcentajes_proteinograma(
    valores: Mapping[str, Any],
) -> dict[str, Decimal]:
    """
    Devuelve ``codigo → %`` para cada fracción ELP presente con PROT_T.
    Claves normalizadas a mayúsculas.
    """
    by_code = {(k or "").strip().upper(): v for k, v in valores.items()}
    prot = by_code.get(CODIGO_PROT_T)
    out: dict[str, Decimal] = {}
    for codigo in CODIGOS_ELP_FRACCIONES:
        pct = porcentaje_fraccion(by_code.get(codigo), prot)
        if pct is not None:
            out[codigo] = pct
    return out


def formatear_pct(pct: Decimal | None) -> str:
    if pct is None:
        return ""
    text = f"{pct:.1f}".replace(".", ",")
    return text


def formatear_gdl(valor: Any) -> str:
    num = _as_decimal(valor)
    if num is None:
        return ""
    # Hasta 2 decimales sin ceros de más innecesarios en enteros.
    q = num.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = f"{q:f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")
