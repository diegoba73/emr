"""Tests Filtros avanzados (cohortes AND/OR + Excel ancho)."""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from laboratorio.cohortes_filtros import filas_ancho, paciente_ids_por_filtro
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestCohortesFiltros(TestCase):
    def setUp(self):
        self.tm = TipoMuestra.objects.create(codigo="SUERO_FA", nombre="Suero", activo=True)
        self.te_lpa = TipoExamen.objects.create(
            codigo="LPA", nombre="Lp(a)", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )
        self.te_glu = TipoExamen.objects.create(
            codigo="GLU", nombre="Glucosa", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )
        self.te_crea = TipoExamen.objects.create(
            codigo="CREATI", nombre="Creatinina", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )

        self.p_both = Paciente.objects.create(dni="111", nombre="Ambos", apellido="A")
        self.p_lpa = Paciente.objects.create(dni="222", nombre="SoloLpa", apellido="B")
        self.p_none = Paciente.objects.create(dni="333", nombre="Ninguno", apellido="C")

        sol1 = SolicitudExamen.objects.create(
            paciente=self.p_both, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO", numero="FA-1"
        )
        ResultadoExamen.objects.create(solicitud=sol1, tipo_examen=self.te_lpa, valor_obtenido="40")
        ResultadoExamen.objects.create(solicitud=sol1, tipo_examen=self.te_glu, valor_obtenido="95")
        SolicitudExamen.objects.filter(pk=sol1.pk).update(estado="FINALIZADO")

        sol2 = SolicitudExamen.objects.create(
            paciente=self.p_lpa, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO", numero="FA-2"
        )
        ResultadoExamen.objects.create(solicitud=sol2, tipo_examen=self.te_lpa, valor_obtenido="50")
        SolicitudExamen.objects.filter(pk=sol2.pk).update(estado="FINALIZADO")

        sol3 = SolicitudExamen.objects.create(
            paciente=self.p_none, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO", numero="FA-3"
        )
        ResultadoExamen.objects.create(solicitud=sol3, tipo_examen=self.te_crea, valor_obtenido="0.9")

        self.lab = User.objects.create_user(username="lab_fa", password="x", rol="laboratorio")
        self.med = User.objects.create_user(username="med_fa", password="x", rol="medico")

    def test_modo_all_vs_any(self):
        all_ids = paciente_ids_por_filtro(["LPA", "GLU"], modo="all")
        any_ids = paciente_ids_por_filtro(["LPA", "GLU"], modo="any")
        self.assertEqual(all_ids, {self.p_both.id})
        self.assertEqual(any_ids, {self.p_both.id, self.p_lpa.id})

    def test_algunos_con_obligatorios(self):
        # LPA obligatorio + GLU/CREATI opcionales → cohorte = quien tiene LPA
        # (los opcionales no recortan el conteo)
        ids = paciente_ids_por_filtro(
            ["LPA", "GLU", "CREATI"],
            modo="any",
            obligatorios=["LPA"],
        )
        self.assertEqual(ids, {self.p_both.id, self.p_lpa.id})

        ids2 = paciente_ids_por_filtro(["LPA"], modo="any", obligatorios=["LPA"])
        self.assertEqual(ids2, {self.p_both.id, self.p_lpa.id})

        # Dos obligatorios → AND
        ids3 = paciente_ids_por_filtro(
            ["LPA", "GLU", "CREATI"],
            modo="any",
            obligatorios=["LPA", "GLU"],
        )
        self.assertEqual(ids3, {self.p_both.id})

    def test_filas_columnas_por_examen(self):
        ids = {self.p_both.id, self.p_lpa.id}
        rows = filas_ancho(
            ["LPA", "GLU"], ids, requeridos=["LPA"]
        )
        self.assertEqual(len(rows), 2)
        by_dni = {r["dni"]: r for r in rows}
        self.assertIn("40", by_dni["111"]["LPA"])
        self.assertIn("95", by_dni["111"]["GLU"])
        self.assertIn("50", by_dni["222"]["LPA"])
        self.assertEqual(by_dni["222"]["GLU"], "")

    def test_api_preview_y_excel(self):
        client = APIClient()
        client.force_authenticate(user=self.med)
        r = client.post(
            "/api/lab/filtros-avanzados/preview/",
            {"codigos": ["LPA", "GLU"], "modo": "all"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["pacientes"], 1)

        r_obl = client.post(
            "/api/lab/filtros-avanzados/preview/",
            {
                "codigos": ["LPA", "GLU"],
                "modo": "any",
                "obligatorios": ["LPA"],
            },
            format="json",
        )
        self.assertEqual(r_obl.status_code, 200)
        # LPA obligatorio + GLU columna → mismos pacientes que solo LPA
        self.assertEqual(r_obl.data["pacientes"], 2)
        self.assertEqual(r_obl.data["obligatorios"], ["LPA"])

        r2 = client.post(
            "/api/lab/filtros-avanzados/excel/",
            {"codigos": ["LPA", "GLU"], "modo": "any"},
            format="json",
        )
        self.assertEqual(r2.status_code, 200)
        self.assertIn("spreadsheetml", r2["Content-Type"])
        self.assertGreater(len(r2.content), 100)
