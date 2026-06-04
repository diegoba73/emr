"""
E2E-1 — Validación reproducible del flujo crítico LIMS/microbiología (API-level).

Sin framework Playwright/Cypress en el repo: un único test de integración HTTP que recorre
solicitud → muestra transaccional → resultado con muestra_id → estudio micro → iniciar →
siembra → lectura → informe preliminar (estado alcanzable sin antibiograma completo).

No imprime payloads clínicos ni codigo_barra. Usuario rol laboratorio con datos sintéticos.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.models_microbiologia import (
    EstudioMicrobiologia,
    InformeMicrobiologia,
    MedioCultivo,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestLimsFlujoCriticoAPI(TestCase):
    """Flujo feliz LIMS + microbiología de punta a punta vía API REST."""

    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_e2e1_{self.suf}",
            email=f"le2e1{self.suf}@test.invalid",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_e2e1_{self.suf}",
            email=f"me2e1{self.suf}@test.invalid",
            password="x",
            rol="medico",
        )
        self.esp = Especialidad.objects.create(nombre=f"Esp E2E1 {self.suf}")
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="E2E",
            matricula=f"M{self.suf}",
            especialidad=self.esp,
            user=self.med_user,
        )
        self.paciente = Paciente.objects.create(
            dni=f"E2E{self.suf}",
            nombre="Pac",
            apellido="Test",
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TM{self.suf[:6]}",
            nombre="Sangre",
            activo=True,
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{self.suf[:6]}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.medio = MedioCultivo.objects.create(
            codigo=f"AG{self.suf[:6]}",
            nombre="Agar test",
            activo=True,
        )
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def _assert_ok(self, response, expected=status.HTTP_200_OK):
        self.assertEqual(
            response.status_code,
            expected,
            f"status inesperado (code={response.status_code})",
        )

    def test_flujo_critico_lims_muestra_resultado_microbiologia(self):
        # 1) Solicitud LIMS
        with self.captureOnCommitCallbacks(execute=True):
            r_sol = self.client.post(
                "/api/lab/solicitudes/",
                {
                    "paciente_id": self.paciente.pk,
                    "medico_id": self.medico.pk,
                    "origen_solicitud": "EMR",
                    "examenes_ids": [self.te.pk],
                },
                format="json",
            )
        self._assert_ok(r_sol, status.HTTP_201_CREATED)
        sol_id = r_sol.json()["id"]
        sol = SolicitudExamen.objects.get(pk=sol_id)
        self.assertEqual(sol.estado, "PENDIENTE")
        resultado = ResultadoExamen.objects.get(solicitud_id=sol_id, tipo_examen_id=self.te.pk)

        # 2) Muestra transaccional: crear → tomar → recibir
        r_m = self.client.post(
            "/api/lab/muestras-transaccionales/",
            {
                "solicitud_id": sol_id,
                "tipo_muestra_id": self.tm.pk,
                "observaciones": "",
            },
            format="json",
        )
        self._assert_ok(r_m, status.HTTP_201_CREATED)
        muestra_id = r_m.json()["id"]
        self.assertEqual(r_m.json()["estado"], "PENDIENTE_TOMA")

        with self.captureOnCommitCallbacks(execute=True):
            r_tomar = self.client.post(
                f"/api/lab/muestras-transaccionales/{muestra_id}/tomar/",
                {},
                format="json",
            )
        self._assert_ok(r_tomar)
        self.assertEqual(r_tomar.json()["estado"], "TOMADA")

        with self.captureOnCommitCallbacks(execute=True):
            r_rec = self.client.post(
                f"/api/lab/muestras-transaccionales/{muestra_id}/recibir/",
                {"ubicacion_actual": "R-E2E1"},
                format="json",
            )
        self._assert_ok(r_rec)
        self.assertEqual(r_rec.json()["estado"], "RECIBIDA")

        # 3) Carga de resultado con muestra_id
        with self.captureOnCommitCallbacks(execute=True):
            r_carga = self.client.post(
                f"/api/lab/solicitudes/{sol_id}/cargar-resultados/",
                {
                    "resultados": [
                        {
                            "id": resultado.pk,
                            "valor": "5.0",
                            "es_patologico": False,
                            "muestra_id": muestra_id,
                        },
                    ],
                },
                format="json",
            )
        self._assert_ok(r_carga)
        resultado.refresh_from_db()
        self.assertEqual(resultado.muestra_id, muestra_id)
        self.assertEqual(resultado.valor_obtenido, "5.0")
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")
        muestra = Muestra.objects.get(pk=muestra_id)
        self.assertEqual(muestra.estado, "EN_PROCESO")

        # 4) Estudio microbiología
        with self.captureOnCommitCallbacks(execute=True):
            r_est = self.client.post(
                "/api/lab/microbiologia/estudios/",
                {
                    "solicitud_id": sol_id,
                    "muestra_id": muestra_id,
                    "tipo_estudio": "CULTIVO_RUTINA",
                },
                format="json",
            )
        self._assert_ok(r_est, status.HTTP_201_CREATED)
        estudio_id = r_est.json()["id"]
        self.assertEqual(r_est.json()["estado"], "PENDIENTE")

        # 5) Iniciar estudio
        with self.captureOnCommitCallbacks(execute=True):
            r_ini = self.client.post(
                f"/api/lab/microbiologia/estudios/{estudio_id}/iniciar/",
                {},
                format="json",
            )
        self._assert_ok(r_ini)
        self.assertEqual(r_ini.json()["estado"], "RECIBIDO")

        # 6) Siembra
        with self.captureOnCommitCallbacks(execute=True):
            r_siem = self.client.post(
                "/api/lab/microbiologia/siembras/",
                {
                    "estudio_id": estudio_id,
                    "medio_id": self.medio.pk,
                    "atmosfera": "aerobia",
                },
                format="json",
            )
        self._assert_ok(r_siem, status.HTTP_201_CREATED)
        siembra_id = r_siem.json()["id"]
        estudio = EstudioMicrobiologia.objects.get(pk=estudio_id)
        self.assertEqual(estudio.estado, "SEMBRADO")

        # 7) Lectura preliminar
        with self.captureOnCommitCallbacks(execute=True):
            r_lect = self.client.post(
                "/api/lab/microbiologia/lecturas/",
                {
                    "siembra_id": siembra_id,
                    "crecimiento": "MODERADO",
                    "es_preliminar": True,
                },
                format="json",
            )
        self._assert_ok(r_lect, status.HTTP_201_CREATED)
        estudio.refresh_from_db()
        self.assertEqual(estudio.estado, "LECTURA_PRELIMINAR")

        # 8) Informe preliminar (estado final alcanzable sin antibiograma completo)
        with self.captureOnCommitCallbacks(execute=True):
            r_inf = self.client.post(
                "/api/lab/microbiologia/informes/",
                {
                    "estudio_id": estudio_id,
                    "tipo": "PRELIMINAR",
                    "texto": "borrador e2e1",
                },
                format="json",
            )
        self._assert_ok(r_inf, status.HTTP_201_CREATED)
        self.assertEqual(r_inf.json()["tipo"], "PRELIMINAR")
        self.assertEqual(r_inf.json()["estado"], "BORRADOR")
        self.assertTrue(
            InformeMicrobiologia.objects.filter(
                pk=r_inf.json()["id"], estudio_id=estudio_id
            ).exists()
        )

        # Rol médico no opera siembra (sanity permisos sin tocar matriz backend)
        self.client.force_authenticate(self.med_user)
        r_med = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {
                "estudio_id": estudio_id,
                "medio_id": self.medio.pk,
                "atmosfera": "aerobia",
            },
            format="json",
        )
        self.assertEqual(r_med.status_code, status.HTTP_403_FORBIDDEN)
