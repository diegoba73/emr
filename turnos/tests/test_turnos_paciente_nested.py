"""Contrato de exposición de ``paciente`` anidado en ``GET /api/turnos/`` (C5.6)."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno

User = get_user_model()

_FORBIDDEN_PACIENTE_KEYS = frozenset(
    {
        "antecedentes_personales",
        "antecedentes_familiares",
        "observaciones",
        "direccion",
        "obra_social",
        "numero_afiliado",
        "fecha_registro",
        "ultima_actualizacion",
        "user",
        "creado_por",
        "modificado_por",
        "creado_por_id",
        "modificado_por_id",
    }
)

_REQUIRED_PACIENTE_KEYS = frozenset(
    {"id", "dni", "nombre", "apellido"}
)


def _staff_medico_client(suffix):
    user = User.objects.create_user(
        username=f"med.turno.{suffix}",
        email=f"med.turno.{suffix}@example.com",
        password="x",
        rol="medico",
        is_staff=True,
    )
    esp, _ = Especialidad.objects.get_or_create(nombre=f"Esp turno {suffix}")
    medico = Medico.objects.create(
        user=user,
        nombre="Dr",
        apellido="Turno",
        matricula=f"MAT-TRN-{suffix[:8]}",
        especialidad=esp,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, medico


def _paciente_con_phi(creator, dni):
    portal = User.objects.create_user(
        username=f"portal.{dni}",
        email=f"portal.{dni}@example.com",
        password="x",
        rol="paciente",
    )
    return Paciente.objects.create(
        dni=dni,
        nombre="Cal",
        apellido="Endario",
        fecha_nacimiento=date(1992, 8, 8),
        user=portal,
        direccion="Calle secreta",
        obra_social="OSDE",
        numero_afiliado="AFF-TUR",
        antecedentes_personales="Secreto",
        antecedentes_familiares="Secreto fam",
        observaciones="Secreto obs",
        creado_por=creator,
        modificado_por=creator,
    )


def _turno(paciente, medico, suffix):
    recurso = Recurso.objects.create(
        nombre=f"Cons Turno {suffix}",
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )
    base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=2)
    return Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=base,
        fecha_hora_fin=base + timedelta(minutes=30),
        estado=Turno.Estado.CONFIRMADO,
        motivo_reserva="Control",
    )


def _results_list(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def _assert_paciente_liviano(paciente_data):
    assert paciente_data is not None
    assert _FORBIDDEN_PACIENTE_KEYS.isdisjoint(paciente_data.keys())
    assert _REQUIRED_PACIENTE_KEYS.issubset(paciente_data.keys())


@pytest.mark.django_db
class TestTurnoPacienteNestedExposure:
    def test_list_turno_paciente_liviano(self):
        creator = User.objects.create_user(
            username="admin.turno.list.creator",
            email="admin.turno.list.creator@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        client, medico = _staff_medico_client("list")
        paciente = _paciente_con_phi(creator, "TRN-LST-001")
        turno = _turno(paciente, medico, "lst")

        response = client.get("/api/turnos/")
        assert response.status_code == status.HTTP_200_OK, response.data

        row = next(r for r in _results_list(response) if r["id"] == turno.id)
        _assert_paciente_liviano(row["paciente"])
        assert row["paciente"]["dni"] == "TRN-LST-001"
        assert "paciente_nombre" in row

    def test_retrieve_turno_paciente_liviano(self):
        creator = User.objects.create_user(
            username="admin.turno.ret.creator",
            email="admin.turno.ret.creator@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        client, medico = _staff_medico_client("ret")
        paciente = _paciente_con_phi(creator, "TRN-RET-001")
        turno = _turno(paciente, medico, "ret")

        response = client.get(f"/api/turnos/{turno.pk}/")
        assert response.status_code == status.HTTP_200_OK, response.data

        _assert_paciente_liviano(response.data["paciente"])
        assert response.data["paciente"]["dni"] == "TRN-RET-001"
        assert response.data["id"] == turno.id
