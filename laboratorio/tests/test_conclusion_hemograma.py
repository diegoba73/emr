"""Tests motor de conclusión de hemograma (reglas + borrador de pantalla)."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from laboratorio.conclusion_hemograma import (
    construir_conclusion_hemograma_reglas,
    parse_valores_borrador,
    sugerir_conclusion_hemograma,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestConclusionHemogramaBorrador(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lab_conc", password="x", rol="laboratorio")
        self.pac = Paciente.objects.create(dni="CONC001", nombre="P", apellido="C")
        self.tm = TipoMuestra.objects.create(codigo="SANGRE_C", nombre="Sangre", activo=True)
        self.te_hgb = TipoExamen.objects.create(
            codigo="HGB", nombre="Hemoglobina", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )
        self.te_hto = TipoExamen.objects.create(
            codigo="HTO", nombre="Hematocrito", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )
        self.te_rbc = TipoExamen.objects.create(
            codigo="HEMATIES", nombre="Hematíes", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO"
        )
        for te in (self.te_hgb, self.te_hto, self.te_rbc):
            ResultadoExamen.objects.create(solicitud=self.sol, tipo_examen=te, valor_obtenido="")

    def test_parse_valores_borrador_dict(self):
        out = parse_valores_borrador({"HGB": "8.5", "HTO": "28", "x": "no"})
        self.assertEqual(out["HGB"], Decimal("8.5"))
        self.assertEqual(out["HTO"], Decimal("28"))
        self.assertNotIn("X", out)

    def test_sugerir_con_borrador_sin_guardar(self):
        data = sugerir_conclusion_hemograma(
            self.sol,
            prefer_medgemma=False,
            valores_borrador=parse_valores_borrador(
                {"HGB": "8.0", "HTO": "28", "HEMATIES": "3.5"}
            ),
        )
        self.assertFalse(data.get("vacio"))
        self.assertIn("Anemia", data["texto"])
        self.assertIn("moderada", data["texto"])
        self.assertEqual(data["fuente"], "reglas")

    def test_prefiere_vcm_chcm_del_borrador(self):
        data = construir_conclusion_hemograma_reglas(
            self.sol,
            valores_borrador=parse_valores_borrador(
                {
                    "HGB": "8.0",
                    "HTO": "28",
                    "HEMATIES": "3.5",
                    "VCM": "70",
                    "CHCM": "28",
                }
            ),
        )
        self.assertEqual(data["detalle"].get("vcm_fuente"), "resultado")
        self.assertEqual(data["detalle"].get("chcm_fuente"), "resultado")
        self.assertEqual(data["detalle"].get("vcm_fl"), "70.0")
        self.assertIn("microcítica", data["texto"])
        self.assertIn("hipocrómica", data["texto"])
        self.assertIn("moderada", data["texto"])  # HGB 8.0

    def test_grados_anisocitosis_y_leucocitosis(self):
        data = construir_conclusion_hemograma_reglas(
            self.sol,
            valores_borrador=parse_valores_borrador(
                {
                    "HGB": "11.0",
                    "HTO": "34",
                    "HEMATIES": "4.0",
                    "VCM": "85",
                    "CHCM": "32.5",
                    "RDW": "17",
                    "LEUCO": "18000",
                }
            ),
        )
        self.assertIn("Anemia leve", data["texto"])
        self.assertIn("anisocitosis moderada", data["texto"])
        self.assertIn("leucocitosis moderada", data["texto"])

    def test_vacio_sin_bd_ni_borrador(self):
        data = construir_conclusion_hemograma_reglas(self.sol)
        self.assertTrue(data.get("vacio"))
        self.assertEqual(data["texto"], "")
