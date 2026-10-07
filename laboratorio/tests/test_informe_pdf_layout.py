"""Tests de agrupación y generación del layout PDF ICPL."""
from __future__ import annotations

import uuid

import pytest
from django.test import TestCase

from reportlab.platypus import PageBreak

from laboratorio.informe_pdf_layout import (
    agrupar_resultados_por_panel,
    construir_story_icpl,
    generar_pdf_icpl_bytes,
    _grupo_es_solo_probnp,
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
        self.assertTrue(grupos[0].panel_codigo)
        self.assertTrue(grupos[1].key.startswith("resultado-"))
        self.assertIsNone(grupos[1].panel_codigo)
        self.assertEqual(len(grupos[1].resultados), 1)

    def test_genera_pdf_valido(self):
        resultados = list(self.sol.resultados.all())
        pdf = generar_pdf_icpl_bytes(self.sol, resultados)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 800)

    def test_contexto_incluye_fecha_extraccion(self):
        from laboratorio.informe_pdf_layout import preparar_contexto_encabezado

        self.sol.fecha_programada_toma = self.sol.fecha_solicitud.date()
        self.sol.save(update_fields=["fecha_programada_toma"])
        ctx = preparar_contexto_encabezado(self.sol)
        self.assertIn("fecha_extraccion", ctx)
        self.assertNotEqual(ctx["fecha_extraccion"], "—")

    def test_firma_bloque_se_carga(self):
        from laboratorio.informe_pdf_config import LABORATORIO_STATIC
        from laboratorio.informe_pdf_layout import _firma_image_reader

        path = LABORATORIO_STATIC / "firmas_bloque.png"
        if not path.is_file():
            path = LABORATORIO_STATIC / "firma_1.png"
        self.assertTrue(path.is_file())
        reader = _firma_image_reader(str(path))
        self.assertIsNotNone(reader)

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


@pytest.mark.django_db
class TestInformePdfProteinograma(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.tm = TipoMuestra.objects.create(codigo=f"SU{tag}", nombre="Suero", activo=True)
        self.panel = PanelExamen.objects.create(
            codigo="PAN_ELP", nombre="Proteinograma electroforético", activo=True
        )
        defs = [
            ("PROT_T", "Proteínas totales", "6.3 - 7.9 g/dL", "g/dL", "6.2"),
            ("ELP_ALB", "Albúmina", "3.57 - 5.48 g/dL", "g/dL", "3.71"),
            ("ELP_A1", "Alfa 1", "0.19 - 0.41 g/dL", "g/dL", "0.28"),
            ("ELP_A2", "Alfa 2", "0.45 - 0.98 g/dL", "g/dL", "0.62"),
            ("ELP_B1", "Beta 1", "0.30 - 0.59 g/dL", "g/dL", "0.55"),
            ("ELP_B2", "Beta 2", "0.20 - 0.55 g/dL", "g/dL", "0.33"),
            ("ELP_GAM", "Gamma", "0.71 - 1.56 g/dL", "g/dL", "0.71"),
            ("ELP_AG", "Relación A/G", "", "", "1.48"),
            ("ELP_CONC", "Conclusiones", "", "", "Proteinograma sin alteraciones significativas"),
        ]
        self.paciente = Paciente.objects.create(dni=f"E{tag}", nombre="Pedro", apellido="Elp")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.paneles.add(self.panel)
        for codigo, nombre, ref, unidad, valor in defs:
            te = TipoExamen.objects.create(
                codigo=codigo,
                nombre=nombre,
                tipo_muestra_requerida=self.tm,
                rango_referencia_texto=ref,
                unidad_default=unidad,
                metodo="Electroforesis capilar",
                precio=1,
                activo=True,
            )
            self.panel.tipos_examen.add(te)
            self.sol.tipos_examen.add(te)
            ResultadoExamen.objects.create(
                solicitud=self.sol,
                tipo_examen=te,
                valor_obtenido=valor,
                unidad=unidad or "",
            )

    def test_pdf_proteinograma_genera_y_agrupa(self):
        resultados = list(
            self.sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        grupos = agrupar_resultados_por_panel(self.sol, resultados)
        self.assertTrue(any(g.panel_codigo == "PAN_ELP" for g in grupos))
        pdf = generar_pdf_icpl_bytes(self.sol, resultados)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 2000)

    def test_bloque_proteinograma_incluye_estructura(self):
        from laboratorio.informe_pdf_layout import GrupoResultadosPdf, _styles
        from laboratorio.proteinograma_pdf import bloque_proteinograma

        resultados = list(
            self.sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        grupo = GrupoResultadosPdf(
            key="panel-PAN_ELP",
            titulo="Proteinograma electroforético",
            resultados=resultados,
            panel_codigo="PAN_ELP",
        )
        flow = bloque_proteinograma(grupo, _styles())
        self.assertTrue(flow)
        self.assertGreaterEqual(len(flow), 1)
        # Sin curva sintética: solo KeepTogether con título/meta/tabla/obs.
        from reportlab.graphics.shapes import Drawing

        for item in flow:
            inner = getattr(item, "_content", None) or getattr(item, "content", None) or []
            self.assertFalse(any(isinstance(x, Drawing) for x in inner))


@pytest.mark.django_db
class TestInformePdfProbnpHojaPropia(TestCase):
    """Pro-BNP debe ir solo en una hoja del PDF (no en UI)."""

    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.tm = TipoMuestra.objects.create(codigo=f"S{tag}", nombre="Suero", activo=True)
        self.te_glu = TipoExamen.objects.create(
            codigo=f"GLU{tag}",
            nombre="Glucemia",
            tipo_muestra_requerida=self.tm,
            unidad_default="mg/dl",
            precio=1,
            activo=True,
        )
        self.te_probnp, _ = TipoExamen.objects.get_or_create(
            codigo="PROBNP",
            defaults={
                "nombre": "Pro-BNP",
                "tipo_muestra_requerida": self.tm,
                "unidad_default": "pg/mL",
                "precio": 1,
                "activo": True,
            },
        )
        self.paciente = Paciente.objects.create(dni=f"P{tag}", nombre="Juan", apellido="Bnp")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.tipos_examen.add(self.te_glu, self.te_probnp)
        self.r_glu = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_glu, valor_obtenido="90", unidad="mg/dl"
        )
        self.r_probnp = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_probnp, valor_obtenido="80", unidad="pg/mL"
        )

    def test_grupo_es_solo_probnp(self):
        from laboratorio.informe_pdf_layout import GrupoResultadosPdf

        g = GrupoResultadosPdf(
            key=f"resultado-{self.r_probnp.id}",
            titulo="Pro-BNP",
            resultados=[self.r_probnp],
        )
        self.assertTrue(_grupo_es_solo_probnp(g))
        g2 = GrupoResultadosPdf(
            key=f"resultado-{self.r_glu.id}",
            titulo="Glucemia",
            resultados=[self.r_glu],
        )
        self.assertFalse(_grupo_es_solo_probnp(g2))

    def test_story_aisla_probnp_con_page_breaks(self):
        resultados = list(
            self.sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        grupos = agrupar_resultados_por_panel(self.sol, resultados)
        self.assertTrue(any(_grupo_es_solo_probnp(g) for g in grupos))

        story = construir_story_icpl(self.sol, resultados)
        breaks = [i for i, x in enumerate(story) if isinstance(x, PageBreak)]
        # Con GLU + PROBNP: un PageBreak entre ambos; la validación no abre otra hoja.
        self.assertEqual(len(breaks), 1)

        pdf = generar_pdf_icpl_bytes(self.sol, resultados)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 800)

    def test_validacion_no_queda_en_hoja_sola_tras_probnp(self):
        """FINALIZADO: el pie de validación sigue en la hoja de Pro-BNP, sin PageBreak extra."""
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        User = get_user_model()
        bio = User.objects.create_user(username=f"bio_{uuid.uuid4().hex[:6]}", password="x")
        self.sol.estado = "FINALIZADO"
        self.sol.save(update_fields=["estado"])
        self.r_probnp.validado_por = bio
        self.r_probnp.fecha_validacion = timezone.now()
        self.r_probnp.save(update_fields=["validado_por", "fecha_validacion"])

        resultados = list(
            self.sol.resultados.select_related(
                "tipo_examen", "tipo_examen__tipo_muestra_requerida", "validado_por"
            )
        )
        story = construir_story_icpl(self.sol, resultados)
        breaks = [i for i, x in enumerate(story) if isinstance(x, PageBreak)]
        self.assertEqual(len(breaks), 1)
        self.assertFalse(isinstance(story[-1], PageBreak))
        # Tras el único PageBreak no debe haber otro salto antes del cierre.
        self.assertFalse(any(isinstance(x, PageBreak) for x in story[breaks[0] + 1 :]))

