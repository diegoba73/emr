"""Tests de escala decimal LabWin Firebird (sin PHI, sin DB clinica)."""
from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase

from laboratorio.labwin_firebird_scale import (
    ResultMeta,
    format_fixed,
    interpret_atomic,
    interpret_result_fld,
    load_results_catalog,
    scale_digit_token,
)


def _meta(abrev="URE", pos=1, dec=1, factor="1", numset=1, formato="1") -> ResultMeta:
    return ResultMeta(
        abrev=abrev,
        posicion=pos,
        tipo=1,
        numset=numset,
        formato=formato,
        decimales=dec,
        factor=Decimal(factor),
    )


class LabwinFirebirdScaleTests(SimpleTestCase):
    def test_152_to_15_2_one_decimal(self):
        out = scale_digit_token("152", _meta(dec=1))
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.valor_clinico, "15.2")
        self.assertEqual(out.valor_numerico, Decimal("15.2"))
        self.assertEqual(out.original, "152")

    def test_1023_to_10_23_two_decimals(self):
        out = scale_digit_token("1023", _meta(abrev="CRE", dec=2))
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.valor_clinico, "10.23")
        self.assertEqual(out.valor_numerico, Decimal("10.23"))

    def test_152_stays_152_when_zero_decimals(self):
        out = scale_digit_token("152", _meta(abrev="GLU", dec=0))
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.valor_clinico, "152")
        self.assertEqual(out.valor_numerico, Decimal("152"))

    def test_negative_sentinel_passthrough(self):
        out = interpret_atomic("-11", _meta(dec=1))
        self.assertEqual(out.status, "passthrough")
        self.assertEqual(out.valor_clinico, "-11")
        self.assertEqual(out.valor_numerico, Decimal("-11"))

    def test_values_below_one(self):
        out = scale_digit_token("025", _meta(dec=1))
        self.assertEqual(out.valor_clinico, "2.5")
        out2 = scale_digit_token("060", _meta(dec=2))
        self.assertEqual(out2.valor_clinico, "0.60")
        self.assertEqual(out2.valor_numerico, Decimal("0.60"))

    def test_explicit_decimal_literal_no_rescale(self):
        out = interpret_atomic("15.2", _meta(dec=1))
        self.assertEqual(out.status, "passthrough")
        self.assertEqual(out.valor_clinico, "15.2")

    def test_text_and_inequalities(self):
        txt = interpret_atomic("Negativo", _meta(dec=0))
        self.assertEqual(txt.status, "textual")
        self.assertEqual(txt.valor_clinico, "Negativo")
        cmp_out = interpret_atomic("<005", _meta(dec=2))
        self.assertEqual(cmp_out.status, "ok")
        self.assertEqual(cmp_out.valor_clinico, "<0.05")
        lit = interpret_atomic("<0.05", _meta(dec=2))
        self.assertEqual(lit.status, "passthrough")
        self.assertEqual(lit.valor_clinico, "<0.05")

    def test_multicomponent_hem(self):
        catalog = {
            ("HEM", 1): _meta("HEM", 1, 0, "10000"),
            ("HEM", 2): _meta("HEM", 2, 1, "0"),
            ("HEM", 3): _meta("HEM", 3, 1, "0"),
            ("HEM", 5): _meta("HEM", 5, 0, "100"),
        }
        raw = "559|400|141||810"
        outs = interpret_result_fld("HEM", raw, catalog)
        self.assertEqual(outs[0].valor_clinico, "5.59")
        self.assertEqual(outs[1].valor_clinico, "40.0")
        self.assertEqual(outs[2].valor_clinico, "14.1")
        self.assertEqual(outs[4].valor_clinico, "81")

    def test_ambiguous_missing_meta_quarantine(self):
        out = scale_digit_token("152", None)
        self.assertEqual(out.status, "quarantine")
        self.assertIsNone(out.valor_clinico)

    def test_undemonstrated_factor_quarantine(self):
        out = scale_digit_token("100", _meta(dec=0, factor="50"))
        self.assertEqual(out.status, "quarantine")
        self.assertIn("undemonstrated_factor", out.reason)

    def test_validated_history_passthrough_literal_unchanged(self):
        """Valor ya en escala clinica (export ancho) no se reescala."""
        out = interpret_atomic("15.2", _meta(dec=1))
        self.assertEqual(out.valor_clinico, "15.2")
        self.assertEqual(out.original, "15.2")

    def test_format_fixed_precision(self):
        self.assertEqual(format_fixed(Decimal("15.2"), 1), "15.2")
        self.assertEqual(format_fixed(Decimal("10.23"), 2), "10.23")
        self.assertEqual(format_fixed(Decimal("152"), 0), "152")

    def test_load_catalog_prefers_tipo1_numset1(self):
        csv_body = (
            "PRV_TIMESTAMP_FLD,ABREV_FLD,NUMERO_FLD,NUMSET_FLD,POSICION_FLD,"
            "TIPO_FLD,METODO_FLD,UNIDADES_FLD,FORMATO_FLD,DECIMALES_FLD,"
            "LIMSUPIM_FLD,LIMSUPMA_FLD,LIMSUPAL_FLD,LIMINFBA_FLD,LIMINFMB_FLD,"
            "LIMINFIM_FLD,VALPRED_FLD,SUMA_FLD,INRESUL_FLD,FACTOR_FLD,"
            "WORKLIST_FLD,RESUTESTTEXT_FLD,DOSCOLUMNAS_FLD,OTROMATERIAL_FLD,"
            "DELTACHKVAL_FLD,DELTACHKDIAS_FLD,MATERIALSTR_FLD,ESTADINTERV_FLD,"
            "WORKLISTWID_FLD,TEXTO_FLD,EXPORTCOLUM_FLD,MAXIMO_FLD,MINIMO_FLD,"
            "INFORESULANT_FLD,AUTOLOAD_FLD,PRV_DELETEDRECORD_FLD\n"
            't,URE,1,1,1,1,,,1,1,,,,,,,,1.0,,,,,,,,,,,,,0\n'
            't,URE,1,0,1,3,,,1,0,,,,,,,,1.0,,,,,,,,,,,,,0\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESULTS.csv"
            path.write_text(csv_body, encoding="utf-8")
            cat = load_results_catalog(path)
        self.assertEqual(cat[("URE", 1)].decimales, 1)
