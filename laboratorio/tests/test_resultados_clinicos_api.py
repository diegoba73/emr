"""
Tests API B4.1 — cargar-resultados estructurados.
"""
import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from auditoria.models import AuditEvent
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestResultadosClinicosAPI(APITestCase):
    def setUp(self):
        suf = "B41"
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f"SNG{suf}", nombre="Sangre", activo=True
        )
        self.tipo_examen = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tipo_muestra,
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
        self.paciente = Paciente.objects.create(
            dni="55667788", nombre="Ana", apellido="B41"
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.user_medico = User.objects.create_user(
            username="med_b41",
            email="med-b41@test.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="B41",
            matricula="M-B41",
            especialidad=esp,
            user=self.user_medico,
        )
        self.user_lab = User.objects.create_user(
            username="lab_b41",
            email="lab-b41@test.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username="adm_b41",
            email="adm-b41@test.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user_lab)

    def _sol_y_res(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="",
        )
        return sol, res

    def test_payload_viejo_sigue_funcionando(self):
        sol, res = self._sol_y_res()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "100", "es_patologico": False}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        res.refresh_from_db()
        self.assertEqual(res.valor_obtenido, "100")

    def test_valor_numerico_y_unidad_default(self):
        sol, res = self._sol_y_res()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {
                        "id": res.pk,
                        "valor": "90",
                        "valor_numerico": 90,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        res.refresh_from_db()
        self.assertEqual(res.valor_numerico, Decimal("90"))
        self.assertEqual(res.unidad, "mg/dL")
        self.assertFalse(res.es_patologico)
        self.assertFalse(res.es_critico)
        self.assertEqual(res.rango_min_snapshot, Decimal("70"))

    def test_fuera_de_rango_patologico(self):
        sol, res = self._sol_y_res()
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "120", "valor_numerico": 120},
                ]
            },
            format="json",
        )
        res.refresh_from_db()
        self.assertTrue(res.es_patologico)

    def test_critico_alto(self):
        sol, res = self._sol_y_res()
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "500", "valor_numerico": 500},
                ]
            },
            format="json",
        )
        res.refresh_from_db()
        self.assertTrue(res.es_critico)

    def test_unidad_explicita_en_payload(self):
        sol, res = self._sol_y_res()
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {
                        "id": res.pk,
                        "valor": "5.0",
                        "valor_numerico": 5.0,
                        "unidad": "mmol/L",
                    }
                ]
            },
            format="json",
        )
        res.refresh_from_db()
        self.assertEqual(res.unidad, "mmol/L")

    def test_cargar_completo_no_finaliza_solo(self):
        sol, res = self._sol_y_res()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "95", "valor_numerico": 95},
                ]
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")

    def test_finalizar_falla_con_vacio(self):
        sol, res = self._sol_y_res()
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/finalizar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_laboratorio_no_auto_finaliza_al_cargar(self):
        sol, res = self._sol_y_res()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "90", "valor_numerico": 90}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")

    def test_bioquimico_valida_y_bloquea(self):
        sol, res = self._sol_y_res()
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "90", "valor_numerico": 90}]},
            format="json",
        )
        user_bio = User.objects.create_user(
            username="bio_b41",
            email="bio-b41@test.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user_lab)
        r_forbid = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r_forbid.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=user_bio)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")
        res.refresh_from_db()
        self.assertEqual(res.validado_por_id, user_bio.id)

        self.client.force_authenticate(user=self.user_lab)
        r_lock = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "91"}]},
            format="json",
        )
        self.assertEqual(r_lock.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medico_no_puede_cargar(self):
        sol, res = self._sol_y_res()
        self.client.force_authenticate(user=self.user_medico)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "90"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_respuesta_incluye_campos_estructurados(self):
        sol, res = self._sol_y_res()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "90", "valor_numerico": 90},
                ]
            },
            format="json",
        )
        data = r.json()
        resultado = data["resultados"][0]
        self.assertIn("valor_numerico", resultado)
        self.assertIn("unidad", resultado)
        self.assertIn("es_critico", resultado)
        self.assertIn("rango_referencia_snapshot", resultado)

    def test_cargar_resultados_metadata_sin_valor_clinico_crudo(self):
        sol, res = self._sol_y_res()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {
                    "resultados": [
                        {"id": res.pk, "valor": "145", "valor_numerico": 145},
                    ]
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ev = (
            AuditEvent.objects.filter(
                entity_type=ResultadoExamen._meta.label,
                entity_id=str(res.pk),
                action="UPDATE",
                module="laboratorio",
            )
            .order_by("-id")
            .first()
        )
        self.assertIsNotNone(ev)
        meta = ev.metadata or {}
        meta_raw = json.dumps(meta, ensure_ascii=False, default=str)
        self.assertNotIn("145", meta_raw)
        for forbidden in (
            "valor_anterior",
            "valor_nuevo",
            "valor_numerico_anterior",
            "valor_numerico_nuevo",
            "unidad_anterior",
            "unidad_nueva",
        ):
            self.assertNotIn(forbidden, meta)
        self.assertTrue(meta.get("valor_presente"))
        self.assertTrue(meta.get("valor_nuevo_presente"))
