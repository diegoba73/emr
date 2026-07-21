"""Fase A — validación bioquímico, bloqueo y flags PDF."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from laboratorio.informe_pdf_layout import _flag_resultado, generar_pdf_icpl_bytes
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestValidacionLimsFaseA(APITestCase):
    def setUp(self):
        suf = "VA"
        self.tm = TipoMuestra.objects.create(codigo=f"S{suf}", nombre="Sangre", activo=True)
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            rango_min=Decimal("70"),
            rango_max=Decimal("110"),
            valor_critico_min=Decimal("40"),
            valor_critico_max=Decimal("400"),
            rango_referencia_texto="70-110 mg/dL",
            precio=1,
            activo=True,
        )
        self.paciente = Paciente.objects.create(dni="99887766", nombre="Val", apellido="Test")
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.user_med = User.objects.create_user(
            username="med_va", email="med-va@t.com", password="x", rol="medico"
        )
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="VA", matricula="M-VA", especialidad=esp, user=self.user_med
        )
        self.user_lab = User.objects.create_user(
            username="lab_va",
            email="lab-va@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_bio = User.objects.create_user(
            username="bio_va",
            email="bio-va@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
            first_name="Ana",
            last_name="Bio",
        )

    def _orden_con_resultado(self, valor="90", valor_numerico=90):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.te)
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.te,
            valor_obtenido="",
        )
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {
                        "id": res.pk,
                        "valor": valor,
                        "valor_numerico": valor_numerico,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        res.refresh_from_db()
        return sol, res

    def test_tecnico_no_valida(self):
        sol, _ = self._orden_con_resultado()
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")

    def test_bioquimico_valida(self):
        sol, res = self._orden_con_resultado()
        self.client.force_authenticate(user=self.user_bio)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        res.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")
        self.assertEqual(res.validado_por_id, self.user_bio.id)
        self.assertIsNotNone(res.fecha_validacion)

    def test_criticos_requieren_confirmacion(self):
        sol, res = self._orden_con_resultado(valor="500", valor_numerico=500)
        self.assertTrue(res.es_critico)
        self.client.force_authenticate(user=self.user_bio)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")

        r2 = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/validar/",
            {"confirmar_criticos": True},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")

    def test_flag_h_l_critico(self):
        sol, res = self._orden_con_resultado(valor="120", valor_numerico=120)
        self.assertEqual(_flag_resultado(res), "H")
        res.valor_numerico = Decimal("50")
        res.es_patologico = True
        res.es_critico = False
        self.assertEqual(_flag_resultado(res), "L")
        res.es_critico = True
        self.assertEqual(_flag_resultado(res), "*")

    def test_pdf_incluye_referencia_y_validacion(self):
        sol, res = self._orden_con_resultado()
        self.client.force_authenticate(user=self.user_bio)
        self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        sol.refresh_from_db()
        res.refresh_from_db()
        resultados = list(
            sol.resultados.select_related("tipo_examen", "validado_por").all()
        )
        pdf = generar_pdf_icpl_bytes(sol, resultados)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 800)
