"""Guardas de cálculos derivados (perfil lipídico / bilirrubina / clearance).

Puras: no requieren base de datos.
"""
from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from laboratorio.calculos_derivados import (
    RESULTADO_NO_CALCULABLE,
    calc_clearance_creatinina,
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

    def test_perfil_ferrico_completo(self):
        out = calcular_derivados(
            {"FERR": Decimal("100"), "UIBC": Decimal("250")}
        )
        self.assertEqual(out["CF"][0], Decimal("350"))
        self.assertEqual(out["SAT_FE"][0], Decimal("28.6"))
        self.assertEqual(out["TRANS"][0], Decimal("280"))

    def test_perfil_ferrico_incompleto_no_calculable(self):
        out = calcular_derivados({"FERR": Decimal("100")})
        self.assertEqual(out["CF"][1], RESULTADO_NO_CALCULABLE)
        self.assertEqual(out["SAT_FE"][1], RESULTADO_NO_CALCULABLE)
        self.assertEqual(out["TRANS"][1], RESULTADO_NO_CALCULABLE)

    def test_clearance_formula_basica(self):
        # (100 × 1500) / (1.0 × 1440) = 104.166… → 104.2
        self.assertEqual(
            calc_clearance_creatinina(
                Decimal("1.0"), Decimal("100"), Decimal("1500")
            ),
            Decimal("104.2"),
        )

    def test_clearance_creatininemia_cero_no_calcula(self):
        self.assertIsNone(
            calc_clearance_creatinina(
                Decimal("0"), Decimal("100"), Decimal("1500")
            )
        )

    def test_clearance_completo(self):
        out = calcular_derivados(
            {
                "CREATI": Decimal("1.0"),
                "CREA_U": Decimal("100"),
                "DIUR": Decimal("1500"),
            }
        )
        self.assertEqual(out["CLEAR_CREA"][0], Decimal("104.2"))
        self.assertEqual(out["CLEAR_CREA"][1], "104.2")

    def test_clearance_incompleto_no_calculable(self):
        out = calcular_derivados(
            {"CREATI": Decimal("1.0"), "CREA_U": Decimal("100")}
        )
        self.assertIsNone(out["CLEAR_CREA"][0])
        self.assertEqual(out["CLEAR_CREA"][1], RESULTADO_NO_CALCULABLE)

    def test_clearance_creatininemia_cero_no_calculable(self):
        out = calcular_derivados(
            {
                "CREATI": Decimal("0"),
                "CREA_U": Decimal("100"),
                "DIUR": Decimal("1500"),
            }
        )
        self.assertIsNone(out["CLEAR_CREA"][0])
        self.assertEqual(out["CLEAR_CREA"][1], RESULTADO_NO_CALCULABLE)

    def test_sin_inputs_clearance_no_emite(self):
        out = calcular_derivados({"COL_TOT": Decimal("200"), "HDL": Decimal("50")})
        self.assertNotIn("CLEAR_CREA", out)
