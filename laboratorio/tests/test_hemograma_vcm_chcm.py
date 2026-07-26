"""Tests backfill VCM/CHCM en órdenes hemograma abiertas."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from laboratorio.hemograma_resultados import asegurar_resultados_panel_hemograma
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestAsegurarHemogramaVcmChcm(TestCase):
    def setUp(self):
        call_command("seed_catalogo_solicitud_papel")
        self.pac = Paciente.objects.create(dni="HEMOVC1", nombre="H", apellido="V")
        self.panel = PanelExamen.objects.get(codigo="PAN_HEMO")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO"
        )
        self.sol.paneles.add(self.panel)
        # Simula orden vieja: solo HGB sin VCM/CHCM
        hgb = TipoExamen.objects.get(codigo="HGB")
        ResultadoExamen.objects.create(solicitud=self.sol, tipo_examen=hgb, valor_obtenido="")
        self.sol.tipos_examen.add(hgb)

    def test_crea_vcm_y_chcm_faltantes(self):
        n = asegurar_resultados_panel_hemograma(self.sol)
        self.assertGreaterEqual(n, 2)
        codigos = set(
            self.sol.resultados.values_list("tipo_examen__codigo", flat=True)
        )
        self.assertIn("VCM", codigos)
        self.assertIn("CHCM", codigos)
        # Idempotente
        self.assertEqual(asegurar_resultados_panel_hemograma(self.sol), 0)
