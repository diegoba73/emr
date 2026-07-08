"""Integración: carga de hemograma completo (ticket Sysmex) vía API."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, SolicitudExamen
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()

# Ticket → valor_sysmex (mínimo para cerrar orden)
HEMO_TICKETS = {
    "HEMATIES": "237",
    "HTO": "217",
    "HGB": "73",
    "RDW": "139",
    "LEU": "93",
    "NEUT_CAY": "70",
    "NEUT_SEG": "70",
    "EOS": "20",
    "BAS": "10",
    "LINF": "204",
    "MONO": "50",
    "PLAQ": "158",
}


@pytest.mark.django_db
class TestCargaHemogramaCompletoAPI:
    def setup_method(self):
        call_command("seed_catalogo_solicitud_papel")
        call_command("migrate", "laboratorio", "0019", verbosity=0)

        self.client = APIClient()
        self.user_lab = User.objects.create_user(
            username="lab_hemo_int",
            email="lab-hemo@test.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user_lab)

        esp = Especialidad.objects.create(nombre="Clínica Hemo")
        med = Medico.objects.create(
            nombre="Med",
            apellido="Test",
            matricula="M-HEMO",
            especialidad=esp,
        )
        self.paciente = Paciente.objects.create(dni="99887766", nombre="Pac", apellido="Hemo")

        panel = PanelExamen.objects.get(codigo="PAN_HEMO")
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.paciente.id,
                "medico_id": med.id,
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "paneles_ids": [panel.id],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED, r.data
        self.sol = SolicitudExamen.objects.get(pk=r.data["id"])

    def _payload_item(self, resultado):
        codigo = resultado.tipo_examen.codigo
        ticket = HEMO_TICKETS[codigo]
        return {
            "id": resultado.id,
            "valor_sysmex": ticket,
        }

    def test_guardar_avance_parcial_y_completo(self):
        self.client.post(f"/api/lab/solicitudes/{self.sol.pk}/tomar-muestra/", {}, format="json")
        resultados = list(self.sol.resultados.select_related("tipo_examen").order_by("id"))
        assert len(resultados) == 12

        parcial = resultados[:3]
        r1 = self.client.post(
            f"/api/lab/solicitudes/{self.sol.pk}/cargar-resultados/",
            {"resultados": [self._payload_item(x) for x in parcial]},
            format="json",
        )
        assert r1.status_code == status.HTTP_200_OK, r1.data
        self.sol.refresh_from_db()
        assert self.sol.estado == "EN_PROCESO"

        r2 = self.client.post(
            f"/api/lab/solicitudes/{self.sol.pk}/cargar-resultados/",
            {"resultados": [self._payload_item(x) for x in resultados]},
            format="json",
        )
        assert r2.status_code == status.HTTP_200_OK, r2.data
        self.sol.refresh_from_db()
        assert self.sol.estado == "FINALIZADO"

    def test_guardar_e_informar_parcial(self):
        self.client.post(f"/api/lab/solicitudes/{self.sol.pk}/tomar-muestra/", {}, format="json")
        resultados = list(self.sol.resultados.select_related("tipo_examen"))
        parcial = resultados[:4]
        r = self.client.post(
            f"/api/lab/solicitudes/{self.sol.pk}/cargar-resultados/",
            {
                "informar_parcial": True,
                "resultados": [self._payload_item(x) for x in parcial],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK, r.data
        self.sol.refresh_from_db()
        assert self.sol.estado == "INFORMADO_PARCIAL"
