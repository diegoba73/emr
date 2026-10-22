"""Guardas de cálculos derivados (perfil lipídico / bilirrubina / clearance).

Puras: no requieren base de datos.
"""
from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from laboratorio.calculos_derivados import (
    RESULTADO_NO_CALCULABLE,
    calc_absoluto_formula,
    calc_ca_ion_zeisler_mg_dl,
    calc_ca_ion_zeisler_mmol_l,
    calc_clearance_creatinina,
    calc_excrecion_mg_dl_a_24h,
    calc_excrecion_por_litro_a_24h,
    calc_ldl_friedewald,
    calc_rac,
    calc_tfg_ckd_epi_2021,
    codigos_insumos_de_calculados,
    codigos_insumos_de_overrideables,
    calcular_derivados,
    es_codigo_calculado,
    format_absoluto_mm3,
    format_valor_formula_leuco_con_absoluto,
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

    def test_proteinuria_24h_formula(self):
        # 80 mg/dL × 1500 mL / 100 = 1200 mg/24 hs
        self.assertEqual(
            calc_excrecion_mg_dl_a_24h(Decimal("80"), Decimal("1500")),
            Decimal("1200"),
        )
        out = calcular_derivados(
            {"PROT_U_EQ": Decimal("80"), "DIUR": Decimal("1500")}
        )
        self.assertEqual(out["PROT_U_24"][0], Decimal("1200"))
        self.assertEqual(out["PROT_U_24"][1], "1200")

    def test_ionograma_y_microalb_24h(self):
        # 100 mmol/L × 1500 / 1000 = 150 mmol/24 hs
        self.assertEqual(
            calc_excrecion_por_litro_a_24h(Decimal("100"), Decimal("1500")),
            Decimal("150"),
        )
        out = calcular_derivados(
            {
                "NA_U": Decimal("100"),
                "K_U": Decimal("40"),
                "CL_U": Decimal("90"),
                "MICROALB": Decimal("20"),
                "DIUR": Decimal("1500"),
            }
        )
        self.assertEqual(out["NA_U24"][1], "150")
        self.assertEqual(out["K_U24"][1], "60")
        self.assertEqual(out["CL_U24"][1], "135")
        # 20 × 1500 / 1000 = 30.0
        self.assertEqual(out["MICROALB_24"][0], Decimal("30.0"))

    def test_orina_24h_sin_diuresis_no_calculable(self):
        out = calcular_derivados({"PROT_U_EQ": Decimal("80"), "NA_U": Decimal("100")})
        self.assertEqual(out["PROT_U_24"][1], RESULTADO_NO_CALCULABLE)
        self.assertEqual(out["NA_U24"][1], RESULTADO_NO_CALCULABLE)

    def test_diur_sola_no_emite_clearance_ni_orina24(self):
        out = calcular_derivados({"DIUR": Decimal("1500")})
        self.assertNotIn("CLEAR_CREA", out)
        self.assertNotIn("PROT_U_24", out)
        self.assertNotIn("NA_U24", out)
        self.assertNotIn("RAC", out)

    def test_rac_formula(self):
        # (30 mg/L ÷ 100 mg/dL) × 100 = 30.0 mg/g
        self.assertEqual(calc_rac(Decimal("30"), Decimal("100")), Decimal("30.0"))
        out = calcular_derivados(
            {"MICROALB": Decimal("30"), "CREA_U": Decimal("100")}
        )
        self.assertEqual(out["RAC"][0], Decimal("30.0"))
        self.assertEqual(out["RAC"][1], "30")

    def test_rac_crea_u_cero_no_calculable(self):
        out = calcular_derivados(
            {"MICROALB": Decimal("30"), "CREA_U": Decimal("0")}
        )
        self.assertIsNone(out["RAC"][0])
        self.assertEqual(out["RAC"][1], RESULTADO_NO_CALCULABLE)

    def test_rac_incompleto_no_calculable(self):
        out = calcular_derivados({"MICROALB": Decimal("30")})
        self.assertEqual(out["RAC"][1], RESULTADO_NO_CALCULABLE)

    def test_insumos_de_rac(self):
        self.assertEqual(
            codigos_insumos_de_calculados(["RAC"]),
            ["MICROALB", "CREA_U"],
        )
        self.assertEqual(codigos_insumos_de_calculados(["RAC", "MICROALB"]), ["CREA_U"])
        self.assertEqual(codigos_insumos_de_calculados(["RAC", "MICROALB", "CREA_U"]), [])

    def test_tfg_ckd_epi_2021_basico(self):
        # Mujer 50 a, Cr 1.0 → 69 mL/min/1.73 m² (CKD-EPI 2021)
        self.assertEqual(
            calc_tfg_ckd_epi_2021(Decimal("1.0"), 50, "F"),
            Decimal("69"),
        )
        out = calcular_derivados(
            {"CREATI": Decimal("1.0")},
            edad_anos=50,
            sexo="F",
        )
        self.assertEqual(out["TFG"][0], Decimal("69"))
        self.assertEqual(out["TFG"][1], "69")

    def test_tfg_sin_demografia_o_menor_no_calculable(self):
        out = calcular_derivados({"CREATI": Decimal("1.0")})
        self.assertEqual(out["TFG"][1], RESULTADO_NO_CALCULABLE)
        self.assertIsNone(calc_tfg_ckd_epi_2021(Decimal("1.0"), 12, "M"))
        self.assertIsNone(calc_tfg_ckd_epi_2021(Decimal("1.0"), 40, "O"))

    def test_insumos_de_tfg(self):
        self.assertEqual(codigos_insumos_de_calculados(["TFG"]), ["CREATI"])
        self.assertEqual(codigos_insumos_de_calculados(["TFG", "CREATI"]), [])
        self.assertTrue(es_codigo_calculado("TFG"))

    def test_insumos_de_clearance_y_orina24(self):
        self.assertEqual(
            set(codigos_insumos_de_calculados(["CLEAR_CREA"])),
            {"CREATI", "CREA_U", "DIUR"},
        )
        self.assertEqual(
            set(codigos_insumos_de_calculados(["MICROALB_24"])),
            {"MICROALB", "DIUR"},
        )
        self.assertEqual(
            set(codigos_insumos_de_calculados(["PROT_U_24", "NA_U24"])),
            {"PROT_U_EQ", "DIUR", "NA_U"},
        )
        self.assertEqual(
            set(codigos_insumos_de_calculados(["LDL", "BIL_I", "CF"])),
            {"COL_TOT", "HDL", "TG", "BIL_T", "BIL_D", "FERR", "UIBC"},
        )

    def test_ca_ion_zeisler_golden(self):
        # CA 7.3 + PROT 5.8 → 3.53 mg/dL → 0.88 mmol/L (÷ 4.008)
        self.assertEqual(
            calc_ca_ion_zeisler_mg_dl(Decimal("7.3"), Decimal("5.8")),
            Decimal("3.53"),
        )
        self.assertEqual(
            calc_ca_ion_zeisler_mmol_l(Decimal("7.3"), Decimal("5.8")),
            Decimal("0.88"),
        )
        out = calcular_derivados(
            {"CA": Decimal("7.3"), "PROT_T": Decimal("5.8")}
        )
        self.assertEqual(out["CA_ION"][1], "0.88")
        self.assertEqual(out["CA_ION"][0], Decimal("0.8800"))
        self.assertFalse(es_codigo_calculado("CA_ION"))

    def test_ca_ion_sin_insumos_completos_no_emite(self):
        self.assertNotIn("CA_ION", calcular_derivados({"CA": Decimal("7.3")}))
        self.assertNotIn("CA_ION", calcular_derivados({"PROT_T": Decimal("5.8")}))

    def test_insumos_ca_ion_overrideable(self):
        self.assertEqual(
            codigos_insumos_de_overrideables(["CA_ION"]),
            ["CA", "PROT_T"],
        )
        self.assertEqual(
            codigos_insumos_de_overrideables(["CA_ION", "CA"]),
            ["PROT_T"],
        )
        self.assertEqual(
            codigos_insumos_de_overrideables(
                ["CA_ION"], paneles=["PAN_EAB_ART"]
            ),
            [],
        )

    def test_absoluto_formula_leucocitaria_etiqueta_mm3(self):
        self.assertEqual(calc_absoluto_formula(Decimal("45"), Decimal("9300")), 4185)
        self.assertEqual(format_absoluto_mm3(4185), "abs. 4.185/mm³")
        self.assertEqual(
            format_valor_formula_leuco_con_absoluto("45", 4185),
            "45%  ·  abs. 4.185/mm³",
        )

