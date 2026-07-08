"""Tests de agrupación y generación del layout PDF ICPL."""
from __future__ import annotations

import uuid

import pytest
from django.test import TestCase

from laboratorio.informe_pdf_layout import (
    agrupar_resultados_por_panel,
    generar_pdf_icpl_bytes,
    _metodo_texto,
    _referencia_texto,
    _valor_y_unidad,
)
from laboratorio.informe_pdf_config import INFORME_TYPO
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente


@pytest.mark.django_db
class TestInformePdfLayout(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.tm = TipoMuestra.objects.create(codigo=f"S{tag}", nombre="Sangre", activo=True)
        self.te1 = TipoExamen.objects.create(
            codigo=f"GLU{tag}",
            nombre="Glucemia",
            tipo_muestra_requerida=self.tm,
            rango_referencia_texto="70 - 110 mg/dl",
            unidad_default="mg/dl",
            precio=1,
            activo=True,
        )
        self.te2 = TipoExamen.objects.create(
            codigo=f"URE{tag}",
            nombre="Uremia",
            tipo_muestra_requerida=self.tm,
            rango_referencia_texto="20 - 40 mg/dl",
            unidad_default="mg/dl",
            precio=1,
            activo=True,
        )
        self.panel = PanelExamen.objects.create(codigo=f"PAN{tag}", nombre="Perfil Lipoproteico", activo=True)
        self.panel.tipos_examen.add(self.te1)

        self.paciente = Paciente.objects.create(dni=f"D{tag}", nombre="Ana", apellido="Test")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.paneles.add(self.panel)
        self.sol.tipos_examen.add(self.te2)

        self.r_panel = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te1, valor_obtenido="82", unidad="mg/dl"
        )
        self.r_suelto = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te2, valor_obtenido="30", unidad="mg/dl"
        )

    def test_agrupar_resultados_por_panel(self):
        resultados = list(self.sol.resultados.all())
        grupos = agrupar_resultados_por_panel(self.sol, resultados)
        self.assertEqual(len(grupos), 2)
        self.assertEqual(grupos[0].titulo, "PERFIL LIPOPROTEICO")
        self.assertEqual(len(grupos[0].resultados), 1)
        self.assertTrue(grupos[1].key.startswith("resultado-"))
        self.assertEqual(len(grupos[1].resultados), 1)

    def test_genera_pdf_valido(self):
        resultados = list(self.sol.resultados.all())
        pdf = generar_pdf_icpl_bytes(self.sol, resultados)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 800)

    def test_valor_y_unidad_separados(self):
        valor, unidad = _valor_y_unidad(self.r_panel)
        self.assertEqual(valor, "82")
        self.assertEqual(unidad, "mg/dl")

    def test_metodo_desde_config_por_codigo(self):
        self.te1.codigo = "GLU"
        self.te1.save(update_fields=["codigo"])
        metodo = _metodo_texto(self.r_panel)
        self.assertEqual(metodo, "Enzimático colorimétrico")

    def test_referencia_sin_duplicar_unidad_en_valor(self):
        ref = _referencia_texto(self.r_panel)
        self.assertIn("70", ref or "")
        valor, unidad = _valor_y_unidad(self.r_panel)
        self.assertNotIn(unidad, valor)

    def test_tipografia_meta_es_dos_tercios_titulo(self):
        self.assertAlmostEqual(
            INFORME_TYPO["exam_meta"] / INFORME_TYPO["exam_title"],
            2 / 3,
            places=2,
        )
