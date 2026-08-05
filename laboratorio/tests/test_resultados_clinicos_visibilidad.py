"""Visibilidad clínica de resultados LIMS: solo FINALIZADO para no-operadores."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestResultadosClinicosVisibilidad:
    def setup_method(self):
        self.suf = uuid.uuid4().hex[:8]
        self.client = APIClient(enforce_csrf_checks=False)
        self.esp = Especialidad.objects.create(nombre=f"Esp RV {self.suf}")
        self.paciente = Paciente.objects.create(
            dni=f"RV{self.suf[:8]}",
            nombre="Pac",
            apellido="ResVis",
        )
        self.med_user = User.objects.create_user(
            username=f"med_rv_{self.suf}",
            email=f"mrv{self.suf}@test.invalid",
            password="x",
            rol="medico",
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="RV",
            matricula=f"MR{self.suf}",
            especialidad=self.esp,
            user=self.med_user,
        )
        self.lab = User.objects.create_user(
            username=f"lab_rv_{self.suf}",
            email=f"lrv{self.suf}@test.invalid",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.sec = User.objects.create_user(
            username=f"sec_rv_{self.suf}",
            email=f"srv{self.suf}@test.invalid",
            password="x",
            rol="secretaria",
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TMR{self.suf[:6]}",
            nombre="Sangre",
            activo=True,
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLR{self.suf[:6]}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.tipos_examen.add(self.te)
        ResultadoExamen.objects.create(
            solicitud=self.sol,
            tipo_examen=self.te,
            valor_obtenido="99.9",
            es_patologico=False,
        )

    def _url(self):
        return f"/api/lab/solicitudes/{self.sol.pk}/"

    def test_medico_ve_orden_sin_resultados_si_no_finalizado(self):
        self.client.force_authenticate(self.med_user)
        r = self.client.get(self._url())
        assert r.status_code == status.HTTP_200_OK
        body = r.json()
        assert body["estado"] == "EN_PROCESO"
        assert body["resultados"] == []
        assert body.get("resultados_visibles") is False

    def test_medico_ve_resultados_si_finalizado(self):
        self.sol.estado = "FINALIZADO"
        self.sol.save(update_fields=["estado"])
        self.client.force_authenticate(self.med_user)
        r = self.client.get(self._url())
        assert r.status_code == status.HTTP_200_OK
        body = r.json()
        assert len(body["resultados"]) == 1
        assert body["resultados"][0]["valor_obtenido"] == "99.9"
        assert body.get("resultados_visibles") is True

    def test_lab_ve_resultados_aunque_en_proceso(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get(self._url())
        assert r.status_code == status.HTTP_200_OK
        body = r.json()
        assert len(body["resultados"]) == 1
        assert body["resultados"][0]["valor_obtenido"] == "99.9"

    def test_secretaria_lista_incluye_en_proceso(self):
        self.client.force_authenticate(self.sec)
        r = self.client.get("/api/lab/solicitudes/")
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        results = data["results"] if isinstance(data, dict) else data
        ids = {row["id"] for row in results}
        assert self.sol.pk in ids
