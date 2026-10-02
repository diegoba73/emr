"""PATCH de cabecera de orden LIMS: editable mientras no FINALIZADO."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import SolicitudExamen
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestSolicitudCabeceraUpdateAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_cab_{self.suf}",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.bio = User.objects.create_user(
            username=f"bio_cab_{self.suf}",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.esp = Especialidad.objects.create(nombre=f"Esp Cab {self.suf}")
        self.medico = Medico.objects.create(
            nombre="Ana",
            apellido="Med",
            matricula=f"MC{self.suf}",
            especialidad=self.esp,
        )
        self.medico_alt = Medico.objects.create(
            nombre="Luis",
            apellido="Alt",
            matricula=f"MA{self.suf}",
            especialidad=self.esp,
        )
        self.paciente = Paciente.objects.create(
            dni=f"PC{self.suf}",
            nombre="Pac",
            apellido="Uno",
        )
        self.paciente_alt = Paciente.objects.create(
            dni=f"PA{self.suf}",
            nombre="Pac",
            apellido="Dos",
        )

    def _crear_orden(self, *, estado="PENDIENTE"):
        return SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado=estado,
            fecha_programada_toma=timezone.localdate(),
            estado_obra_social="AUTORIZADO",
        )

    def test_lab_patch_cabecera_pendiente(self):
        sol = self._crear_orden(estado="PENDIENTE")
        self.client.force_authenticate(user=self.lab)
        r = self.client.patch(
            f"/api/lab/solicitudes/{sol.id}/",
            {
                "paciente_id": self.paciente_alt.id,
                "medico_id": self.medico_alt.id,
                "observaciones": "corregido lab",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        sol.refresh_from_db()
        self.assertEqual(sol.paciente_id, self.paciente_alt.id)
        self.assertEqual(sol.medico_interno_id, self.medico_alt.id)
        self.assertEqual(sol.observaciones, "corregido lab")
        get_r = self.client.get(f"/api/lab/solicitudes/{sol.id}/")
        self.assertEqual(get_r.status_code, status.HTTP_200_OK)
        self.assertEqual(get_r.data.get("paciente"), self.paciente_alt.id)
        self.assertEqual(get_r.data.get("medico_interno"), self.medico_alt.id)

    def test_bio_patch_en_proceso_y_listo(self):
        for estado in ("EN_PROCESO", "LISTO_PARA_VALIDAR"):
            sol = self._crear_orden(estado=estado)
            self.client.force_authenticate(user=self.bio)
            r = self.client.patch(
                f"/api/lab/solicitudes/{sol.id}/",
                {"observaciones": f"ok {estado}"},
                format="json",
            )
            self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
            sol.refresh_from_db()
            self.assertEqual(sol.observaciones, f"ok {estado}")
            self.assertEqual(sol.estado, estado)

    def test_patch_finalizado_rechazado(self):
        sol = self._crear_orden(estado="FINALIZADO")
        self.client.force_authenticate(user=self.lab)
        r = self.client.patch(
            f"/api/lab/solicitudes/{sol.id}/",
            {"observaciones": "no debe"},
            format="json",
        )
        self.assertIn(r.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        sol.refresh_from_db()
        self.assertNotEqual(sol.observaciones, "no debe")
