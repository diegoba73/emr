"""Guardas de cálculos derivados (perfil lipídico / bilirrubina)."""
from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from laboratorio.calculos_derivados import (
    RESULTADO_NO_CALCULABLE,
    calc_ldl_friedewald,
    calcular_derivados,
)


class TestCalculosDerivados(TestCase):
    def test_friedewald_tg_400_no_calcula_ldl(self):
        self.assertIsNone(
            calc_ldl_friedewald(Decimal("200"), Decimal("50"), Decimal("400"))
        )

    def test_perfil_completo_calcula_ldl(self):
        out = calcular_derivados(
            {
                "COL_TOT": Decimal("200"),
                "HDL": Decimal("50"),
                "TG": Decimal("150"),
            }
        )
        self.assertEqual(out["LDL"][0], Decimal("120"))
        self.assertNotEqual(out["LDL"][1], RESULTADO_NO_CALCULABLE)

    def test_tg_alto_marca_no_calculable(self):
        out = calcular_derivados(
            {
                "COL_TOT": Decimal("200"),
                "HDL": Decimal("50"),
                "TG": Decimal("450"),
            }
        )
        self.assertIsNone(out["LDL"][0])
        self.assertEqual(out["LDL"][1], RESULTADO_NO_CALCULABLE)
        self.assertIsNone(out["COL_RESID"][0])
        self.assertEqual(out["COL_RESID"][1], RESULTADO_NO_CALCULABLE)
        # VLDL sí es calculable (TG/5)
        self.assertEqual(out["VLDL"][0], Decimal("90"))

    def test_sin_tg_no_inventa_ldl_vldl(self):
        out = calcular_derivados(
            {"COL_TOT": Decimal("200"), "HDL": Decimal("50")}
        )
        self.assertEqual(out["LDL"][1], RESULTADO_NO_CALCULABLE)
        self.assertEqual(out["VLDL"][1], RESULTADO_NO_CALCULABLE)
        self.assertEqual(out["COL_RESID"][1], RESULTADO_NO_CALCULABLE)
        self.assertIn("COL_NO_LDL", out)

    def test_sin_col_hdl_no_emite_lipidicos(self):
        out = calcular_derivados({"TG": Decimal("150")})
        self.assertNotIn("LDL", out)
        self.assertNotIn("VLDL", out)

    def test_bil_i_invalida_cuando_bd_mayor_bt(self):
        out = calcular_derivados(
            {"BIL_T": Decimal("0.5"), "BIL_D": Decimal("0.8")}
        )
        self.assertEqual(out["BIL_I"][1], RESULTADO_NO_CALCULABLE)
        self.assertIsNone(out["BIL_I"][0])
