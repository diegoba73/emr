"""CTOG: panel basal + 120 min (sin 60) y bloque PDF."""
from __future__ import annotations

import uuid

import pytest
from django.test import TestCase

from laboratorio.ctog import CODIGOS_CTOG, PANEL_CTOG, TITULO_INFORME_CTOG
from laboratorio.ctog_pdf import bloque_ctog
from laboratorio.informe_pdf_layout import (
    GrupoResultadosPdf,
    _styles,
    agrupar_resultados_por_panel,
    generar_pdf_icpl_bytes,
)
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente


@pytest.mark.django_db
class TestCtogPanelInforme(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.tm, _ = TipoMuestra.objects.get_or_create(
            codigo="SUERO",
            defaults={"nombre": "Suero", "activo": True},
        )
        self.panel, _ = PanelExamen.objects.get_or_create(
            codigo=PANEL_CTOG,
            defaults={
                "nombre": "Curva de tolerancia a la glucosa (CTOG)",
                "activo": True,
            },
        )
        defs = [
            ("GLU_0", "Basal (0 min)", "70–99 mg/dL", "89"),
            ("GLU120", "120 minutos", "Menor de 140 mg/dL", "112"),
        ]
        self.paciente = Paciente.objects.create(dni=f"C{tag}", nombre="Ana", apellido="Ctog")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.paneles.add(self.panel)
        for codigo, nombre, ref, valor in defs:
            te, _ = TipoExamen.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "tipo_muestra_requerida": self.tm,
                    "rango_referencia_texto": ref,
                    "unidad_default": "mg/dL",
                    "metodo": "Enzimático",
                    "precio": 1,
                    "activo": True,
                },
            )
            self.panel.tipos_examen.add(te)
            self.sol.tipos_examen.add(te)
            ResultadoExamen.objects.create(
                solicitud=self.sol,
                tipo_examen=te,
                valor_obtenido=valor,
                unidad="mg/dL",
            )

    def test_agrupa_como_panel_ctog(self):
        resultados = list(
            self.sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        grupos = agrupar_resultados_por_panel(self.sol, resultados)
        self.assertTrue(any(g.panel_codigo == PANEL_CTOG for g in grupos))
        grupo = next(g for g in grupos if g.panel_codigo == PANEL_CTOG)
        codigos = [
            (r.tipo_examen.codigo or "").strip().upper() for r in grupo.resultados
        ]
        self.assertEqual(tuple(codigos), CODIGOS_CTOG)
        self.assertNotIn("GLU60", codigos)

    def test_pdf_ctog_genera(self):
        resultados = list(
            self.sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        pdf = generar_pdf_icpl_bytes(self.sol, resultados)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 2000)

    def test_bloque_ctog_estructura(self):
        resultados = list(
            self.sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        grupo = GrupoResultadosPdf(
            key=f"panel-{PANEL_CTOG}",
            titulo="Curva de tolerancia a la glucosa (CTOG)",
            resultados=resultados,
            panel_codigo=PANEL_CTOG,
        )
        flow = bloque_ctog(grupo, _styles())
        self.assertTrue(flow)
        self.assertGreaterEqual(len(flow), 1)

        def _walk(item) -> list[str]:
            out: list[str] = []
            if hasattr(item, "text") and item.text:
                out.append(str(item.text))
            inner = getattr(item, "_content", None) or getattr(item, "content", None)
            if inner:
                for child in inner:
                    out.extend(_walk(child))
            cells = getattr(item, "_cellvalues", None)
            if cells:
                for row in cells:
                    for cell in row:
                        out.extend(_walk(cell))
            return out

        blob = " ".join(_walk(flow[0]))
        self.assertIn(TITULO_INFORME_CTOG, blob)
        self.assertIn("Basal", blob)
        self.assertIn("120", blob)
        self.assertNotIn("60 minutos", blob)
        self.assertIn("75 g", blob)
