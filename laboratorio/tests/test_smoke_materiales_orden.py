"""Smoke: orden LCR, esputo y mixta (sangre + LCR) — tubos, toma y talón."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra, TipoContenedor
from laboratorio.orden_grupos_informe import construir_grupos_informe, ordenar_grupos_por_defecto
from laboratorio.talon_pedido_pdf import generar_talon_solicitud_pdf_bytes
from laboratorio.tubos_catalogo import FRASCO_ESTERIL, SUERO
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestSmokeMaterialesOrden(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_materiales_pedido")

    def setUp(self):
        self.tag = uuid.uuid4().hex[:6]
        self.lab = User.objects.create_user(
            username=f"smoke_lab_{self.tag}",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"9{self.tag}",
            nombre="Karina",
            apellido="Ardiles",
        )
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)
        self.frasco = TipoContenedor.objects.get(codigo=FRASCO_ESTERIL)
        self.suero, _ = TipoContenedor.objects.get_or_create(
            codigo=SUERO,
            defaults={"nombre": "Tubo Suero", "color": "Rojo", "activo": True},
        )
        self.tm_suero, _ = TipoMuestra.objects.get_or_create(
            codigo="SUERO",
            defaults={"nombre": "Suero", "activo": True},
        )

    def _sol_con(self, *examenes: TipoExamen) -> SolicitudExamen:
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(*examenes)
        for ex in examenes:
            ResultadoExamen.objects.get_or_create(
                solicitud=sol, tipo_examen=ex, defaults={"valor_obtenido": ""}
            )
        return sol

    def test_smoke_lcr_tubo_frasco_esteril_talon_y_orden_analitos(self):
        asp = TipoExamen.objects.get(codigo="ASP_LCR")
        rbc = TipoExamen.objects.get(codigo="RBC_LCR")
        glu = TipoExamen.objects.get(codigo="GLU_LCR")
        for ex in (asp, rbc, glu):
            self.assertEqual(ex.tipo_contenedor_id, self.frasco.pk, ex.codigo)
            self.assertEqual(ex.tipo_muestra_requerida.codigo, "LCR")

        sol = self._sol_con(asp, rbc, glu)

        prev = self.client.get(f"/api/lab/solicitudes/{sol.pk}/tubos-preview/")
        self.assertEqual(prev.status_code, status.HTTP_200_OK, prev.content)
        tubos = prev.json()["tubos"]
        self.assertEqual(len(tubos), 1)
        self.assertEqual(tubos[0]["tipo_contenedor_codigo"], FRASCO_ESTERIL)

        toma = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/tomar-muestra/", {}, format="json"
        )
        self.assertEqual(toma.status_code, status.HTTP_200_OK, toma.content)
        m = Muestra.objects.get(solicitud=sol)
        self.assertEqual(m.tipo_contenedor.codigo, FRASCO_ESTERIL)
        self.assertEqual(m.estado, "PENDIENTE_TOMA")

        pdf = generar_talon_solicitud_pdf_bytes(sol)
        self.assertTrue(pdf.startswith(b"%PDF"))
        talon = self.client.get(f"/api/lab/solicitudes/{sol.pk}/talon-pdf/")
        self.assertEqual(talon.status_code, status.HTTP_200_OK, talon.content)

        grupos = ordenar_grupos_por_defecto(
            construir_grupos_informe(sol, sol.resultados.select_related("tipo_examen"))
        )
        codigos = []
        for g in grupos:
            if g.resultados:
                te = g.resultados[0].tipo_examen
                codigos.append(te.codigo)
        self.assertEqual(codigos[:3], ["ASP_LCR", "RBC_LCR", "GLU_LCR"])

    def test_smoke_esputo_tubo_frasco_esteril(self):
        citol = TipoExamen.objects.get(codigo="CITOL_ESP")
        self.assertEqual(citol.tipo_contenedor_id, self.frasco.pk)
        sol = self._sol_con(citol)
        prev = self.client.get(f"/api/lab/solicitudes/{sol.pk}/tubos-preview/")
        self.assertEqual(prev.status_code, status.HTTP_200_OK)
        self.assertEqual(prev.json()["tubos"][0]["tipo_contenedor_codigo"], FRASCO_ESTERIL)
        toma = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/tomar-muestra/", {}, format="json"
        )
        self.assertEqual(toma.status_code, status.HTTP_200_OK, toma.content)
        self.assertEqual(Muestra.objects.get(solicitud=sol).tipo_contenedor.codigo, FRASCO_ESTERIL)

    def test_smoke_orden_mixta_sangre_y_lcr_dos_tubos(self):
        glu_sangre = TipoExamen.objects.create(
            codigo=f"GLU_S{self.tag}"[:20],
            nombre="Glucemia suero smoke",
            tipo_muestra_requerida=self.tm_suero,
            tipo_contenedor=self.suero,
            precio=1,
            activo=True,
        )
        glu_lcr = TipoExamen.objects.get(codigo="GLU_LCR")
        sol = self._sol_con(glu_sangre, glu_lcr)

        prev = self.client.get(f"/api/lab/solicitudes/{sol.pk}/tubos-preview/")
        self.assertEqual(prev.status_code, status.HTTP_200_OK, prev.content)
        tubos = prev.json()["tubos"]
        codigos = {t["tipo_contenedor_codigo"] for t in tubos}
        self.assertEqual(codigos, {SUERO, FRASCO_ESTERIL})
        self.assertEqual(sum(t["cantidad"] for t in tubos), 2)

        toma = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/tomar-muestra/", {}, format="json"
        )
        self.assertEqual(toma.status_code, status.HTTP_200_OK, toma.content)
        muestras = list(Muestra.objects.filter(solicitud=sol))
        self.assertEqual(len(muestras), 2)
        self.assertEqual(
            {m.tipo_contenedor.codigo for m in muestras},
            {SUERO, FRASCO_ESTERIL},
        )
        pdf = generar_talon_solicitud_pdf_bytes(sol)
        self.assertTrue(pdf.startswith(b"%PDF"))
