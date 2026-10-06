"""Tests proteinograma: % desde g/dL y panel PAN_ELP."""
from decimal import Decimal

from django.test import SimpleTestCase

from laboratorio.catalogo_solicitud_papel import PANELES
from laboratorio.proteinograma import (
    CODIGO_ELP_AG,
    CODIGO_PROT_T,
    CODIGOS_ELP_FRACCIONES,
    PANEL_ELP,
    formatear_gdl,
    formatear_pct,
    porcentaje_fraccion,
    porcentajes_proteinograma,
)


class TestProteinogramaHelper(SimpleTestCase):
    def test_panel_elp_incluye_prot_t_y_ag(self):
        panel = next(p for p in PANELES if p["codigo"] == PANEL_ELP)
        comps = panel["componentes"]
        self.assertEqual(comps[0], CODIGO_PROT_T)
        self.assertIn(CODIGO_ELP_AG, comps)
        for codigo in CODIGOS_ELP_FRACCIONES:
            self.assertIn(codigo, comps)
        self.assertEqual(comps[-1], "ELP_CONC")

    def test_porcentaje_fraccion_ejemplo_imagen(self):
        # PROT_T=6.2, ALB=3.71 → 59.8 %
        pct = porcentaje_fraccion("3.71", "6.2")
        self.assertEqual(pct, Decimal("59.8"))
        self.assertEqual(formatear_pct(pct), "59,8")

    def test_porcentajes_proteinograma_fixture_imagen(self):
        valores = {
            "PROT_T": Decimal("6.2"),
            "ELP_ALB": Decimal("3.71"),
            "ELP_A1": Decimal("0.28"),
            "ELP_A2": Decimal("0.62"),
            "ELP_B1": Decimal("0.55"),
            "ELP_B2": Decimal("0.33"),
            "ELP_GAM": Decimal("0.71"),
        }
        pct = porcentajes_proteinograma(valores)
        self.assertEqual(pct["ELP_ALB"], Decimal("59.8"))
        self.assertEqual(pct["ELP_A1"], Decimal("4.5"))
        self.assertEqual(pct["ELP_A2"], Decimal("10.0"))
        self.assertEqual(pct["ELP_B1"], Decimal("8.9"))
        self.assertLessEqual(abs(pct["ELP_B2"] - Decimal("5.4")), Decimal("0.1"))
        self.assertLessEqual(abs(pct["ELP_GAM"] - Decimal("11.4")), Decimal("0.1"))

    def test_formatear_gdl(self):
        self.assertEqual(formatear_gdl(Decimal("6.2")), "6,2")
        self.assertEqual(formatear_gdl("3.71"), "3,71")

    def test_porcentaje_sin_total_es_none(self):
        self.assertIsNone(porcentaje_fraccion(3.71, None))
        self.assertIsNone(porcentaje_fraccion(3.71, 0))
        self.assertEqual(porcentajes_proteinograma({"ELP_ALB": 3.71}), {})
