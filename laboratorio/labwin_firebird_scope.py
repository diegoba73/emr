"""
Alcance de protocolos Firebird LabWin para audit/rectify de escala.

Invariante: fecha de protocolo > ``until`` nunca entra en escritura (ni en apply).
"""
from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from laboratorio.labwin_csv import format_protocolo_labwin
from laboratorio.labwin_firebird import _cell, _is_active, parse_fb_date

DEFAULT_SCALE_UNTIL = date(2026, 9, 29)


@dataclass(frozen=True)
class ScopeBuildResult:
    """protocolo LW -> NUMERO_FLD Firebird; conteos agregados sin PHI."""

    target_protos: dict[str, str]
    skipped_after_until: int
    skipped_r2_filter: int


def build_firebird_protocol_scope(
    pacientes_csv: Path,
    *,
    until: date,
    since: date | None = None,
    only_r2_delta: bool = False,
    wide_protocols: Iterable[str] | None = None,
) -> ScopeBuildResult:
    """
    Arma el set de protocolos en alcance.

    - Siempre: ``fecha <= until``.
    - Si ``only_r2_delta``: además ``fecha > since`` y protocolo ausente de ``wide_protocols``.
    """
    wide = set(wide_protocols or ())
    target: dict[str, str] = {}
    skipped_after_until = 0
    skipped_r2 = 0

    with Path(pacientes_csv).open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not _is_active(row):
                continue
            num = _cell(row, "NUMERO_FLD")
            fecha = parse_fb_date(_cell(row, "FECHA_FLD"))
            if not num or not fecha:
                continue
            lw = format_protocolo_labwin(fecha, num)
            if not lw:
                continue
            if fecha > until:
                skipped_after_until += 1
                continue
            if only_r2_delta:
                if since is None or fecha <= since or lw in wide:
                    skipped_r2 += 1
                    continue
            target[lw] = num

    return ScopeBuildResult(
        target_protos=target,
        skipped_after_until=skipped_after_until,
        skipped_r2_filter=skipped_r2,
    )
