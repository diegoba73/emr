"""Alcance --until para audit/rectify de escala LabWin (sin PHI)."""
from __future__ import annotations

import csv
import tempfile
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from laboratorio.labwin_firebird_scope import (
    DEFAULT_SCALE_UNTIL,
    build_firebird_protocol_scope,
)


def _write_pacientes(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["NUMERO_FLD", "FECHA_FLD", "PRV_DELETEDRECORD_FLD"],
        )
        w.writeheader()
        for num, fecha in rows:
            w.writerow(
                {
                    "NUMERO_FLD": num,
                    "FECHA_FLD": fecha,
                    "PRV_DELETEDRECORD_FLD": "0",
                }
            )


class LabwinFirebirdScopeTests(SimpleTestCase):
    def test_default_until_is_2026_09_29(self):
        self.assertEqual(DEFAULT_SCALE_UNTIL, date(2026, 9, 29))

    def test_until_includes_29_excludes_30(self):
        with tempfile.TemporaryDirectory() as tmp:
            pacientes = Path(tmp) / "PACIENTES.csv"
            _write_pacientes(
                pacientes,
                [
                    ("10001", "20260929"),
                    ("10002", "20260930"),
                    ("10003", "20261001"),
                ],
            )
            scope = build_firebird_protocol_scope(
                pacientes,
                until=date(2026, 9, 29),
                only_r2_delta=False,
            )
            self.assertIn("LW-2026-10001", scope.target_protos)
            self.assertNotIn("LW-2026-10002", scope.target_protos)
            self.assertNotIn("LW-2026-10003", scope.target_protos)
            self.assertEqual(scope.skipped_after_until, 2)

    def test_only_r2_respects_until_and_since(self):
        with tempfile.TemporaryDirectory() as tmp:
            pacientes = Path(tmp) / "PACIENTES.csv"
            _write_pacientes(
                pacientes,
                [
                    ("20001", "20260810"),  # <= since
                    ("20002", "20260820"),  # in window
                    ("20003", "20260929"),  # in window
                    ("20004", "20260930"),  # after until
                ],
            )
            scope = build_firebird_protocol_scope(
                pacientes,
                until=date(2026, 9, 29),
                since=date(2026, 8, 12),
                only_r2_delta=True,
                wide_protocols=set(),
            )
            self.assertEqual(
                set(scope.target_protos),
                {"LW-2026-20002", "LW-2026-20003"},
            )
            self.assertEqual(scope.skipped_after_until, 1)
