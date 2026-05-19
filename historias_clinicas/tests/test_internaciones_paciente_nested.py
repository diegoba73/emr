"""Contrato de exposición de ``paciente`` en ``GET /api/internaciones/`` (C5.4).

API legacy: ``api.views.InternacionViewSet`` + ``historias_clinicas.Internacion``
(no confundir con ``/api/internacion/internaciones/`` de la app ``internacion``).
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalogos.models import AreaInternacion, CamaInternacion, CentroFisico
from historias_clinicas.models import Internacion
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()

_FORBIDDEN_PACIENTE_KEYS = frozenset(
    {
        "antecedentes_personales",
        "antecedentes_familiares",
        "observaciones",
        "user",
        "creado_por",
        "modificado_por",
        "creado_por_id",
        "modificado_por_id",
        "obra_social",
        "numero_afiliado",
        "fecha_registro",
        "ultima_actualizacion",
    }
)

_REQUIRED_PACIENTE_KEYS = frozenset(
    {"id", "dni", "nombre", "apellido", "fecha_nacimiento"}
)


def _admin_client(suffix):
    user = User.objects.create_user(
        username=f"admin.int.{suffix}",
        email=f"admin.int.{suffix}@example.com",
        password="x",
        rol="ADMIN",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _cama_internacion(suffix):
    centro, _ = CentroFisico.objects.get_or_create(
        codigo="CEHTA",
        defaults={"nombre": "CEHTA Test"},
    )
    area, _ = AreaInternacion.objects.get_or_create(
        codigo="UCO",
        defaults={
            "nombre": "UCO Test",
            "centro_fisico": centro,
        },
    )
    return CamaInternacion.objects.create(
        numero=f"INT-{suffix[:12]}",
        area=area,
    )


def _paciente_con_phi(creator, dni):
    return Paciente.objects.create(
        dni=dni,
        nombre="Int",
        apellido="Paciente",
        fecha_nacimiento=date(1980, 4, 4),
        antecedentes_personales="Secreto",
        antecedentes_familiares="Secreto fam",
        observaciones="Secreto obs",
        obra_social="OSDE",
        numero_afiliado="AFF-INT",
        creado_por=creator,
        modificado_por=creator,
    )


def _internacion(paciente, cama, medico=None):
    return Internacion.objects.create(
        paciente=paciente,
        medico_responsable=medico,
        cama=cama,
        fecha_ingreso=timezone.now(),
        motivo_ingreso="Control",
        estado="ACTIVA",
    )


def _assert_paciente_liviano(paciente_data):
    assert paciente_data is not None
    assert _FORBIDDEN_PACIENTE_KEYS.isdisjoint(paciente_data.keys())
    assert _REQUIRED_PACIENTE_KEYS.issubset(paciente_data.keys())


@pytest.mark.django_db
class TestInternacionPacienteNestedExposure:
    def test_retrieve_paciente_liviano(self):
        creator = User.objects.create_user(
            username="admin.int.creator",
            email="admin.int.creator@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        client = _admin_client("retrieve")
        paciente = _paciente_con_phi(creator, "INT-RET-001")
        cama = _cama_internacion("ret")
        internacion = _internacion(paciente, cama)

        response = client.get(f"/api/internaciones/{internacion.pk}/")
        assert response.status_code == status.HTTP_200_OK, response.data

        _assert_paciente_liviano(response.data["paciente"])
        assert response.data["paciente"]["dni"] == "INT-RET-001"
        assert response.data["id"] == internacion.id
        assert "motivo_ingreso" in response.data

    def test_list_paciente_liviano(self):
        creator = User.objects.create_user(
            username="admin.int.list.creator",
            email="admin.int.list.creator@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        client = _admin_client("list")
        paciente = _paciente_con_phi(creator, "INT-LST-001")
        cama = _cama_internacion("lst")
        internacion = _internacion(paciente, cama)

        response = client.get("/api/internaciones/")
        assert response.status_code == status.HTTP_200_OK, response.data

        results = response.data
        if isinstance(results, dict) and "results" in results:
            results = results["results"]
        row = next(r for r in results if r["id"] == internacion.id)
        _assert_paciente_liviano(row["paciente"])

    def test_medico_ve_su_internacion_con_paciente_liviano(self):
        creator = User.objects.create_user(
            username="admin.int.med.creator",
            email="admin.int.med.creator@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        user_med = User.objects.create_user(
            username="med.int.nested",
            email="med.int.nested@example.com",
            password="x",
            rol="medico",
        )
        esp, _ = Especialidad.objects.get_or_create(nombre="Esp Int Nested")
        medico = Medico.objects.create(
            user=user_med,
            nombre="Dr",
            apellido="Int",
            matricula="MAT-INT-NST",
            especialidad=esp,
        )
        client = APIClient()
        client.force_authenticate(user=user_med)

        paciente = _paciente_con_phi(creator, "INT-MED-001")
        cama = _cama_internacion("med")
        internacion = _internacion(paciente, cama, medico=medico)

        response = client.get(f"/api/internaciones/{internacion.pk}/")
        assert response.status_code == status.HTTP_200_OK, response.data
        _assert_paciente_liviano(response.data["paciente"])
