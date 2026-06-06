"""
E2E-1 / E2E-1-A — Validación reproducible del flujo crítico LIMS/microbiología (API-level).

Sin framework Playwright/Cypress en el repo: tests de integración HTTP que recorren
solicitud → muestra transaccional → resultado con muestra_id → estudio micro → …
→ informe preliminar (E2E-1) o cierre FINAL / VALIDADO / INFORMADO (E2E-1-A).

No imprime payloads clínicos ni codigo_barra. Usuario rol laboratorio con datos sintéticos.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.models_microbiologia import (
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    InformeMicrobiologia,
    MedioCultivo,
    Microorganismo,
    SiembraMicrobiologia,
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
        self.admin = User.objects.create_user(
            username=f"adm_e2e1a_{self.suf}",
            email=f"ae2e1a{self.suf}@test.invalid",
            password="x",
            rol="admin",
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

    def _crear_contexto_lims_base(self):
        """Solicitud LIMS + resultado pendiente."""
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
        return sol_id, resultado

    def _crear_muestra_recibida(self, sol_id):
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
        return muestra_id

    def _cargar_resultado_con_muestra(self, sol_id, muestra_id, resultado):
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
        sol = SolicitudExamen.objects.get(pk=sol_id)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")
        muestra = Muestra.objects.get(pk=muestra_id)
        self.assertEqual(muestra.estado, "EN_PROCESO")

    def _crear_estudio_micro_iniciado(self, sol_id, muestra_id):
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

        with self.captureOnCommitCallbacks(execute=True):
            r_ini = self.client.post(
                f"/api/lab/microbiologia/estudios/{estudio_id}/iniciar/",
                {},
                format="json",
            )
        self._assert_ok(r_ini)
        self.assertEqual(r_ini.json()["estado"], "RECIBIDO")
        return estudio_id

    def _crear_siembra_y_lectura(self, estudio_id, *, es_preliminar=True):
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

        with self.captureOnCommitCallbacks(execute=True):
            r_lect = self.client.post(
                "/api/lab/microbiologia/lecturas/",
                {
                    "siembra_id": siembra_id,
                    "crecimiento": "MODERADO",
                    "es_preliminar": es_preliminar,
                },
                format="json",
            )
        self._assert_ok(r_lect, status.HTTP_201_CREATED)
        lectura_id = r_lect.json()["id"]
        if es_preliminar:
            estudio.refresh_from_db()
            self.assertEqual(estudio.estado, "LECTURA_PRELIMINAR")
        return siembra_id, lectura_id

    def test_flujo_critico_lims_muestra_resultado_microbiologia(self):
        sol_id, resultado = self._crear_contexto_lims_base()
        muestra_id = self._crear_muestra_recibida(sol_id)
        self._cargar_resultado_con_muestra(sol_id, muestra_id, resultado)
        estudio_id = self._crear_estudio_micro_iniciado(sol_id, muestra_id)
        self._crear_siembra_y_lectura(estudio_id)

        # Informe preliminar (estado final alcanzable sin antibiograma completo)
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

        # Rol médico no opera siembra: 403 sin side effects
        siembras_antes = SiembraMicrobiologia.objects.filter(estudio_id=estudio_id).count()
        audit_siembras_antes = AuditEvent.objects.filter(
            entity_type=SiembraMicrobiologia._meta.label,
            action="CREATE",
            metadata__accion="crear_siembra",
            metadata__estudio_id=estudio_id,
        ).count()
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
        self.assertEqual(
            SiembraMicrobiologia.objects.filter(estudio_id=estudio_id).count(),
            siembras_antes,
        )
        self.assertEqual(
            AuditEvent.objects.filter(
                entity_type=SiembraMicrobiologia._meta.label,
                action="CREATE",
                metadata__accion="crear_siembra",
                metadata__estudio_id=estudio_id,
            ).count(),
            audit_siembras_antes,
        )

    def test_flujo_critico_lims_microbiologia_final_validado_informado(self):
        micro = Microorganismo.objects.create(
            codigo=f"EC{self.suf[:6]}",
            nombre="E. coli test",
            genero="Escherichia",
            especie="coli",
            activo=True,
        )
        antibiotico = Antibiotico.objects.create(
            codigo=f"AB{self.suf[:6]}",
            nombre="Ampicilina test",
            activo=True,
        )

        sol_id, resultado = self._crear_contexto_lims_base()
        muestra_id = self._crear_muestra_recibida(sol_id)
        self._cargar_resultado_con_muestra(sol_id, muestra_id, resultado)
        estudio_id = self._crear_estudio_micro_iniciado(sol_id, muestra_id)
        _, lectura_id = self._crear_siembra_y_lectura(estudio_id, es_preliminar=False)

        with self.captureOnCommitCallbacks(execute=True):
            r_aisl = self.client.post(
                "/api/lab/microbiologia/aislados/",
                {
                    "estudio_id": estudio_id,
                    "lectura_id": lectura_id,
                    "significancia": "SIGNIFICATIVO",
                    "requiere_antibiograma": True,
                },
                format="json",
            )
        self._assert_ok(r_aisl, status.HTTP_201_CREATED)
        aislado_id = r_aisl.json()["id"]
        self.assertEqual(r_aisl.json()["estado"], "SOSPECHADO")

        with self.captureOnCommitCallbacks(execute=True):
            r_id = self.client.post(
                "/api/lab/microbiologia/identificaciones/",
                {
                    "aislado_id": aislado_id,
                    "microorganismo_id": micro.pk,
                    "metodo": "MALDI-TOF",
                    "resultado": "E. coli",
                    "confianza": "98.50",
                },
                format="json",
            )
        self._assert_ok(r_id, status.HTTP_201_CREATED)
        estudio = EstudioMicrobiologia.objects.get(pk=estudio_id)
        self.assertEqual(estudio.estado, "IDENTIFICACION")

        with self.captureOnCommitCallbacks(execute=True):
            r_ag = self.client.post(
                "/api/lab/microbiologia/antibiogramas/",
                {"aislado_id": aislado_id, "metodo": "Disco difusión"},
                format="json",
            )
        self._assert_ok(r_ag, status.HTTP_201_CREATED)
        antibiograma_id = r_ag.json()["id"]
        estudio.refresh_from_db()
        self.assertEqual(estudio.estado, "ANTIBIOGRAMA")

        with self.captureOnCommitCallbacks(execute=True):
            r_res = self.client.post(
                "/api/lab/microbiologia/resultados-antibiotico/",
                {
                    "antibiograma_id": antibiograma_id,
                    "antibiotico_id": antibiotico.pk,
                    "interpretacion": "S",
                    "halo_mm": "20.00",
                },
                format="json",
            )
        self._assert_ok(r_res, status.HTTP_201_CREATED)

        with self.captureOnCommitCallbacks(execute=True):
            r_comp = self.client.post(
                f"/api/lab/microbiologia/antibiogramas/{antibiograma_id}/completar/",
                {},
                format="json",
            )
        self._assert_ok(r_comp)
        self.assertEqual(r_comp.json()["estado"], "COMPLETO")
        self.assertTrue(
            Antibiograma.objects.filter(pk=antibiograma_id, estado="COMPLETO").exists()
        )

        with self.captureOnCommitCallbacks(execute=True):
            r_inf = self.client.post(
                "/api/lab/microbiologia/informes/",
                {
                    "estudio_id": estudio_id,
                    "tipo": "FINAL",
                    "texto": "borrador final e2e1a",
                },
                format="json",
            )
        self._assert_ok(r_inf, status.HTTP_201_CREATED)
        informe_id = r_inf.json()["id"]
        self.assertEqual(r_inf.json()["tipo"], "FINAL")
        self.assertEqual(r_inf.json()["estado"], "BORRADOR")

        with self.captureOnCommitCallbacks(execute=True):
            r_emit = self.client.post(
                f"/api/lab/microbiologia/informes/{informe_id}/emitir/",
                {"texto": "Informe final cultivo e2e1a."},
                format="json",
            )
        self._assert_ok(r_emit)
        self.assertEqual(r_emit.json()["estado"], "EMITIDO")
        estudio.refresh_from_db()
        self.assertEqual(estudio.estado, "LISTO_PARA_VALIDAR")

        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r_val = self.client.post(
                f"/api/lab/microbiologia/informes/{informe_id}/validar/",
                {},
                format="json",
            )
        self._assert_ok(r_val)
        self.assertEqual(r_val.json()["estado"], "VALIDADO")
        estudio.refresh_from_db()
        self.assertEqual(estudio.estado, "VALIDADO")

        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r_info = self.client.post(
                f"/api/lab/microbiologia/estudios/{estudio_id}/marcar-informado/",
                {},
                format="json",
            )
        self._assert_ok(r_info)
        self.assertEqual(r_info.json()["estado"], "INFORMADO")
        estudio.refresh_from_db()
        self.assertEqual(estudio.estado, "INFORMADO")

        n_siembras = SiembraMicrobiologia.objects.filter(estudio_id=estudio_id).count()
        r_bloq = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {
                "estudio_id": estudio_id,
                "medio_id": self.medio.pk,
                "atmosfera": "aerobia",
            },
            format="json",
        )
        self.assertEqual(r_bloq.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            SiembraMicrobiologia.objects.filter(estudio_id=estudio_id).count(),
            n_siembras,
        )
