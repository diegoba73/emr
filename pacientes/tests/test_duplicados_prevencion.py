"""Prevención de duplicados al alta de pacientes."""
from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.models import Paciente
from pacientes.tests.test_api import _admin, _payload_create


@pytest.mark.django_db
class TestPrevencionDuplicadosAlta:
    def test_post_dni_duplicado_mensaje_claro(self):
        Paciente.objects.create(
            dni="DUP-DNI-1",
            nombre="Ana",
            apellido="Existente",
            fecha_nacimiento=date(1990, 1, 1),
        )
        client = APIClient()
        client.force_authenticate(user=_admin("admin.dup.dni"))
        response = client.post(
            "/api/pacientes/",
            _payload_create(dni="DUP-DNI-1", nombre="Otra", apellido="Persona"),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "dni" in response.data
        assert "Ya existe un paciente con este DNI" in str(response.data["dni"])
        assert Paciente.objects.filter(dni="DUP-DNI-1").count() == 1

    def test_candidatos_por_dni_bloquea_alta(self):
        existente = Paciente.objects.create(
            dni="DUP-CAND-9",
            nombre="Luis",
            apellido="Demo",
            fecha_nacimiento=date(1985, 3, 3),
        )
        client = APIClient()
        client.force_authenticate(user=_admin("admin.dup.cand"))
        response = client.get(
            "/api/pacientes/candidatos-duplicado/", {"dni": "DUP-CAND-9"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["bloquea_alta"] is True
        assert any(
            r["paciente"]["id"] == existente.id and r["match"] == "dni"
            for r in response.data["resultados"]
        )

    def test_candidatos_por_identidad_sin_bloquear(self):
        existente = Paciente.objects.create(
            dni="DUP-ID-A",
            nombre="MARIA",
            apellido="LOPEZ",
            fecha_nacimiento=date(1992, 7, 7),
        )
        client = APIClient()
        client.force_authenticate(user=_admin("admin.dup.id"))
        response = client.get(
            "/api/pacientes/candidatos-duplicado/",
            {
                "dni": "DUP-ID-B",
                "nombre": "maria",
                "apellido": "lopez",
                "fecha_nacimiento": "1992-07-07",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["bloquea_alta"] is False
        assert any(
            r["paciente"]["id"] == existente.id and r["match"] == "identidad"
            for r in response.data["resultados"]
        )

    def test_candidatos_sin_criterios_400(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.dup.empty"))
        response = client.get("/api/pacientes/candidatos-duplicado/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
