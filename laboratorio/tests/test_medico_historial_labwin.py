"""Médico: ficha + historial LabWin FINALIZADO sin vínculo clínico."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestMedicoHistorialLabwinFicha(APITestCase):
    def setUp(self):
        tm = TipoMuestra.objects.create(codigo="SNG_LW", nombre="Sangre", activo=True)
        self.tipo = TipoExamen.objects.create(
            codigo="GLU_LW",
            nombre="Glucemia",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            precio=1,
            activo=True,
        )
        self.paciente = Paciente.objects.create(
            dni="55667788", nombre="Historial", apellido="Labwin"
        )
        esp = Especialidad.objects.create(nombre="Clínica LW")
        self.user_med = User.objects.create_user(
            username="med_lw_hist",
            email="med-lw@test.com",
            password="x",
            rol="medico",
            is_staff=False,
        )
        Medico.objects.create(
            nombre="Med",
            apellido="LW",
            matricula="M-LW-H",
            especialidad=esp,
            user=self.user_med,
        )
        self.sol_lw = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="EXTERNO_ICPL",
            estado="EN_PROCESO",
            numero="LW-2025-00999",
            medico_interno=None,
        )
        ResultadoExamen.objects.create(
            solicitud=self.sol_lw,
            tipo_examen=self.tipo,
            valor_obtenido="95",
            valor_numerico=Decimal("95"),
            unidad="mg/dL",
        )
        SolicitudExamen.objects.filter(pk=self.sol_lw.pk).update(estado="FINALIZADO")
        self.sol_lw.refresh_from_db()
        self.sol_pendiente_ajena = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            numero="LAB-OTRO-1",
        )

    def test_medico_retrieve_paciente_sin_vinculo(self):
        self.client.force_authenticate(user=self.user_med)
        r = self.client.get(f"/api/pacientes/{self.paciente.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["dni"], "55667788")

        r_list = self.client.get("/api/pacientes/")
        self.assertEqual(r_list.status_code, status.HTTP_200_OK)
        # Listado paginado sigue restringido a vínculos (is_staff=False).
        ids = {row["id"] for row in r_list.data.get("results", [])}
        self.assertNotIn(self.paciente.id, ids)

    def test_medico_lista_todas_las_ordenes_del_paciente(self):
        self.client.force_authenticate(user=self.user_med)
        r_global = self.client.get("/api/lab/solicitudes/")
        self.assertEqual(r_global.status_code, status.HTTP_200_OK)
        ids_global = {row["id"] for row in r_global.data["results"]}
        self.assertIn(self.sol_lw.id, ids_global)
        self.assertIn(self.sol_pendiente_ajena.id, ids_global)

        r = self.client.get(f"/api/lab/solicitudes/?paciente={self.paciente.id}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in r.data["results"]}
        self.assertIn(self.sol_lw.id, ids)
        self.assertIn(self.sol_pendiente_ajena.id, ids)

        r_detail = self.client.get(f"/api/lab/solicitudes/{self.sol_lw.id}/")
        self.assertEqual(r_detail.status_code, status.HTTP_200_OK)
        self.assertTrue(r_detail.data.get("resultados_visibles", True))
        valores = [x["valor_obtenido"] for x in (r_detail.data.get("resultados") or [])]
        self.assertIn("95", valores)

    def test_medico_no_escribe_cargar_resultados_en_labwin(self):
        self.client.force_authenticate(user=self.user_med)
        res = self.sol_lw.resultados.first()
        r = self.client.post(
            f"/api/lab/solicitudes/{self.sol_lw.id}/cargar-resultados/",
            {"resultados": [{"id": res.id, "valor": "100"}]},
            format="json",
        )
        self.assertIn(r.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))
