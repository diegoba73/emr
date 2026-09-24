from datetime import date
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from laboratorio.labwin_firebird import unpack_result, load_firebird_delta, parse_fb_date


class FirebirdUnpackTests(SimpleTestCase):
    def test_parse_yyyymmdd(self):
        self.assertEqual(parse_fb_date("20260813"), date(2026, 8, 13))

    def test_unpack_hem_pipe(self):
        raw = "1|2|3|4|5|6|7|8|9|10|11|obs|x"
        out = unpack_result("HEM", raw)
        self.assertEqual(out["HEMATIES"], "1")
        self.assertEqual(out["HGB"], "3")
        self.assertEqual(out["LEUCO"], "5")
        self.assertNotIn("obs", out.values())

    def test_unpack_simple_ure(self):
        self.assertEqual(unpack_result("URE", "40"), {"UREA": "40"})

    def test_hem_not_collapsed_to_hematies_without_pipe(self):
        self.assertEqual(unpack_result("HEM", "solo"), {})


class FirebirdLoadFixtureTests(TestCase):
    def test_load_requires_scale_catalog(self):
        # minimal synthetic CSVs
        import tempfile
        import csv

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for name, fields, rows in (
                (
                    "PACIENTES.csv",
                    ["NUMERO_FLD", "FECHA_FLD", "HCLIN_FLD", "PRV_DELETEDRECORD_FLD"],
                    [["90001", "20260820", "30111222", "0"]],
                ),
                (
                    "DETERS.csv",
                    [
                        "NUMERO_FLD",
                        "ABREV_FLD",
                        "RESULT_FLD",
                        "PRV_DELETEDRECORD_FLD",
                    ],
                    [["90001", "URE", "35", "0"], ["90001", "GLU", "90", "0"]],
                ),
                (
                    "HCLINICA.csv",
                    ["NUMERO_FLD", "NOMBRE_FLD", "PRV_DELETEDRECORD_FLD"],
                    [["30111222", "PRUEBA,PACIENTE", "0"]],
                ),
            ):
                with (d / name).open("w", encoding="utf-8", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=fields)
                    w.writeheader()
                    for row in rows:
                        w.writerow(dict(zip(fields, row)))

            patients, orders, stats = load_firebird_delta(
                d,
                wide_protocols=set(),
                since=date(2026, 8, 12),
                lims_codes={"UREA", "GLU"},
            )
            self.assertEqual(stats.orders_built, 0)
            self.assertEqual(orders, [])
            self.assertTrue(any('RESULTS.csv ausente' in warning for warning in stats.warnings))

            (d / 'RESULTS.csv').write_text(
                'ABREV_FLD,NUMSET_FLD,POSICION_FLD,TIPO_FLD,FORMATO_FLD,DECIMALES_FLD,FACTOR_FLD,PRV_DELETEDRECORD_FLD\n'
                'URE,1,1,1,1,0,1,0\n'
                'GLU,1,1,1,1,0,1,0\n',
                encoding='utf-8',
            )
            patients, orders, stats = load_firebird_delta(
                d, wide_protocols=set(), since=date(2026, 8, 12), lims_codes={'UREA', 'GLU'},
            )
            self.assertEqual(stats.orders_built, 1)
            self.assertEqual(orders[0].protocolo, "LW-2026-90001")
            self.assertEqual(orders[0].resultados["UREA"], "35")
            self.assertIn("30111222", patients)
