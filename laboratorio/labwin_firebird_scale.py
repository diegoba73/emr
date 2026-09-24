"""
Interpretación de escala decimal LabWin Firebird (RESULT_FLD × RESULTS.DECIMALES_FLD).

Regla demostrada vs todo_labwin.csv (~99% pares numéricos):
  dígitos enteros -> Decimal(n) / 10**DECIMALES_FLD

Excepciones demostradas (panel HEM):
  pos1 Hematies: n * FACTOR / 1e6 (FACTOR=10000)
  pos5 Leucocitos: n * FACTOR / 1e3 (FACTOR=100)

Casos ambiguos -> cuarentena (sin valor clinico inventado).
No modifica resultados nativos SYNESIS.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

_DIGITS = re.compile(r"^\d+$")
_SIGNED_INT = re.compile(r"^-\d+$")
_DECIMAL_LITERAL = re.compile(r"^-?\d+\.\d+$")
_COMPARATOR = re.compile(r"^([<>]=?)(.+)$")
_HAS_ALPHA = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class ResultMeta:
    abrev: str
    posicion: int
    tipo: int
    numset: int
    formato: str
    decimales: int
    factor: Decimal


@dataclass(frozen=True)
class ScaleOutcome:
    original: str
    valor_clinico: str | None
    valor_numerico: Decimal | None
    status: str
    reason: str = ""


def _parse_int(raw: str, default: int = 0) -> int:
    text = (raw or "").strip().strip('"')
    if not text:
        return default
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return default


def _parse_factor(raw: str) -> Decimal:
    text = (raw or "").strip().strip('"')
    if not text:
        return Decimal("1")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("1")


def load_results_catalog(results_csv: Path) -> dict[tuple[str, int], ResultMeta]:
    """Indice (ABREV, POSICION) -> meta TIPO=1 preferida (NUMSET=1 si hay)."""
    buckets: dict[tuple[str, int], list[ResultMeta]] = {}
    with Path(results_csv).open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            deleted = (row.get("PRV_DELETEDRECORD_FLD") or "").strip().strip('"')
            if deleted not in ("", "0", "False", "false"):
                continue
            tipo = _parse_int(row.get("TIPO_FLD") or "0")
            if tipo != 1:
                continue
            abrev = (row.get("ABREV_FLD") or "").strip().strip('"')
            if not abrev:
                continue
            pos = _parse_int(row.get("POSICION_FLD") or "1", 1)
            meta = ResultMeta(
                abrev=abrev,
                posicion=pos,
                tipo=tipo,
                numset=_parse_int(row.get("NUMSET_FLD") or "0"),
                formato=(row.get("FORMATO_FLD") or "").strip().strip('"'),
                decimales=max(0, _parse_int(row.get("DECIMALES_FLD") or "0")),
                factor=_parse_factor(row.get("FACTOR_FLD") or "1"),
            )
            buckets.setdefault((abrev, pos), []).append(meta)

    catalog: dict[tuple[str, int], ResultMeta] = {}
    for key, rows in buckets.items():
        preferred = [r for r in rows if r.numset == 1] or rows
        if len({r.decimales for r in preferred}) > 1:
            continue
        if len({r.factor for r in preferred}) > 1:
            continue
        catalog[key] = preferred[0]
    return catalog


def format_fixed(value: Decimal, places: int) -> str:
    if places <= 0:
        return str(int(value))
    q = value.quantize(Decimal(10) ** -places)
    return format(q, "f")


def format_trim(value: Decimal, max_places: int) -> str:
    text = format_fixed(value, max_places)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _factor_is_identity(factor: Decimal) -> bool:
    return factor in (Decimal("0"), Decimal("0.0"), Decimal("1"), Decimal("1.0"))


def scale_digit_token(
    digits: str,
    meta: ResultMeta | None,
    *,
    panel: str | None = None,
    pos: int | None = None,
) -> ScaleOutcome:
    original = digits
    if not _DIGITS.match(digits):
        return ScaleOutcome(original, None, None, "quarantine", "not_digits")
    if meta is None:
        return ScaleOutcome(original, None, None, "quarantine", "missing_results_meta")

    n = int(digits)
    d = meta.decimales
    f = meta.factor
    panel_u = (panel or meta.abrev or "").strip().upper()
    position = pos if pos is not None else meta.posicion

    if panel_u == "HEM" and position == 1 and f == Decimal("10000"):
        value = (Decimal(n) * f) / Decimal("1000000")
        return ScaleOutcome(original, format_trim(value, 2), value, "ok", "hem_hematies_factor")

    if panel_u == "HEM" and position == 5 and f == Decimal("100"):
        value = (Decimal(n) * f) / Decimal("1000")
        return ScaleOutcome(original, format_trim(value, 1), value, "ok", "hem_leu_factor")

    if not _factor_is_identity(f):
        return ScaleOutcome(original, None, None, "quarantine", f"undemonstrated_factor={f}")

    value = Decimal(n) / (Decimal(10) ** d)
    return ScaleOutcome(original, format_fixed(value, d), value, "ok", f"div_10^{d}")


def interpret_atomic(
    raw: str,
    meta: ResultMeta | None,
    *,
    panel: str | None = None,
    pos: int | None = None,
) -> ScaleOutcome:
    original = (raw or "").strip()
    if not original:
        return ScaleOutcome(original, None, None, "quarantine", "empty")

    if _DECIMAL_LITERAL.match(original):
        try:
            num = Decimal(original)
        except InvalidOperation:
            return ScaleOutcome(original, original, None, "textual", "decimal_literal_invalid")
        return ScaleOutcome(original, original, num, "passthrough", "decimal_literal")

    if _SIGNED_INT.match(original):
        return ScaleOutcome(original, original, Decimal(original), "passthrough", "signed_sentinel")

    m = _COMPARATOR.match(original)
    if m:
        cmp_op, tail = m.group(1), m.group(2).strip()
        if _DIGITS.match(tail):
            inner = scale_digit_token(tail, meta, panel=panel, pos=pos)
            if inner.status != "ok" or inner.valor_clinico is None:
                return ScaleOutcome(
                    original, None, None, "quarantine", f"comparator_{inner.reason}"
                )
            return ScaleOutcome(
                original,
                f"{cmp_op}{inner.valor_clinico}",
                inner.valor_numerico,
                "ok",
                "comparator_scaled",
            )
        if _DECIMAL_LITERAL.match(tail):
            try:
                num = Decimal(tail)
            except InvalidOperation:
                num = None
            return ScaleOutcome(original, original, num, "passthrough", "comparator_literal")
        return ScaleOutcome(original, original, None, "textual", "comparator_text")

    if _HAS_ALPHA.search(original) and not _DIGITS.match(original):
        return ScaleOutcome(original, original, None, "textual", "alpha_text")

    if _DIGITS.match(original):
        return scale_digit_token(original, meta, panel=panel, pos=pos)

    return ScaleOutcome(original, original, None, "textual", "unclassified_shape")


def interpret_result_fld(
    abrev: str,
    result_fld: str,
    catalog: dict[tuple[str, int], ResultMeta],
) -> list[ScaleOutcome]:
    raw = (result_fld or "").strip()
    abrev_u = (abrev or "").strip()
    if not raw:
        return [ScaleOutcome("", None, None, "quarantine", "empty")]

    if "|" in raw:
        return [
            interpret_atomic(part.strip(), catalog.get((abrev_u, i)), panel=abrev_u, pos=i)
            for i, part in enumerate(raw.split("|"), start=1)
        ]

    return [interpret_atomic(raw, catalog.get((abrev_u, 1)), panel=abrev_u, pos=1)]
