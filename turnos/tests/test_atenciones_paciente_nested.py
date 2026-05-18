"""Contrato de exposición de ``paciente`` anidado en ``GET /api/atenciones/`` (C5.2 / C5.3)."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno

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
        "alergias",
        "medicacion_actual",
    }
)

_REQUIRED_PACIENTE_KEYS = frozenset(
    {"id", "dni", "nombre", "apellido", "fecha_nacimiento"}
)

_REQUIRED_TURNO_KEYS = frozenset(
    {"id", "estado", "fecha_hora_inicio", "paciente", "paciente_id"}
)


def _medico_client(username_suffix):
    user = User.objects.create_user(
        username=f"med.nested.{username_suffix}",
        email=f"med.nested.{username_suffix}@example.com",
        password="x",
        rol="medico",
    )
    esp, _ = Especialidad.objects.get_or_create(
        nombre=f"Esp nested {username_suffix}"
    )
    medico = Medico.objects.create(
        user=user,
        nombre="Dr",
        apellido="Nested",
        matricula=f"MAT-NST-{username_suffix[:8]}",
        especialidad=esp,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, medico


def _paciente_con_phi_extra(creator=None, **kwargs):
    defaults = {
        "nombre": "Ana",
        "apellido": "Nested",
        "fecha_nacimiento": date(1985, 6, 10),
        "antecedentes_personales": "Antecedente secreto",
        "antecedentes_familiares": "Familiar secreto",
        "observaciones": "Observación secreta",
        "obra_social": "OSPE",
        "numero_afiliado": "AFF-999",
    }
    defaults.update(kwargs)
    if creator:
        defaults["creado_por"] = creator
        defaults["modificado_por"] = creator
    return Paciente.objects.create(**defaults)


def _atencion_con_turno(client, medico, paciente, suffix):
    recurso = Recurso.objects.create(
        nombre=f"Cons Nested {suffix}",
        ubicacion="P1",
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=timezone.now() + timedelta(hours=1),
        fecha_hora_fin=timezone.now() + timedelta(hours=2),
        estado="CONFIRMADO",
        motivo_reserva="Control",
    )
    atencion = Atencion.objects.create(
        turno=turno,
        paciente=paciente,
        medico_principal=medico,
        tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
    )
    return atencion, turno


def _assert_paciente_liviano(paciente_data):
    assert paciente_data is not None
    assert _FORBIDDEN_PACIENTE_KEYS.isdisjoint(paciente_data.keys())
    assert _REQUIRED_PACIENTE_KEYS.issubset(paciente_data.keys())


@pytest.mark.django_db
class TestAtencionPacienteNestedExposure:
    def test_retrieve_paciente_sin_phi_ni_trazabilidad_ids(self):
        creator = User.objects.create_user(
            username="admin.nested.creator",
            email="admin.nested.creator@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        portal_user = User.objects.create_user(
            username="portal.nested.pac",
            email="portal.nested.pac@example.com",
            password="x",
            rol="paciente",
        )
        client, _, medico = _medico_client("retrieve")

        paciente = _paciente_con_phi_extra(
            creator,
            dni="NST-RET-001",
            user=portal_user,
        )
        atencion, _ = _atencion_con_turno(client, medico, paciente, "ret")

        response = client.get(reverse("atenciones-detail", kwargs={"pk": atencion.pk}))
        assert response.status_code == status.HTTP_200_OK, response.data

        _assert_paciente_liviano(response.data["paciente"])
        assert response.data["paciente"]["dni"] == "NST-RET-001"

    def test_list_paciente_anidado_liviano(self):
        client, _, medico = _medico_client("list")
        paciente = _paciente_con_phi_extra(dni="NST-LST-001")
        atencion = Atencion.objects.create(
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
        )

        response = client.get(reverse("atenciones-list"))
        assert response.status_code == status.HTTP_200_OK, response.data

        results = response.data
        if isinstance(results, dict) and "results" in results:
            results = results["results"]
        row = next(r for r in results if r["id"] == atencion.id)
        _assert_paciente_liviano(row["paciente"])

    def test_retrieve_turno_paciente_tambien_liviano(self):
        creator = User.objects.create_user(
            username="admin.nested.turno",
            email="admin.nested.turno@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        client, _, medico = _medico_client("turno-light")
        paciente = _paciente_con_phi_extra(creator, dni="NST-TUR-002")
        atencion, turno = _atencion_con_turno(client, medico, paciente, "tur")

        response = client.get(reverse("atenciones-detail", kwargs={"pk": atencion.pk}))
        assert response.status_code == status.HTTP_200_OK

        turno_block = response.data["turno"]
        assert turno_block is not None
        assert turno_block["id"] == turno.id
        assert _REQUIRED_TURNO_KEYS.issubset(turno_block.keys())
        assert "atencion" not in turno_block

        turno_paciente = turno_block["paciente"]
        _assert_paciente_liviano(turno_paciente)
        assert turno_paciente["dni"] == "NST-TUR-002"

    def test_list_turno_paciente_tambien_liviano(self):
        client, _, medico = _medico_client("list-turno")
        paciente = _paciente_con_phi_extra(dni="NST-LST-TUR-001")
        atencion, _ = _atencion_con_turno(client, medico, paciente, "lst-tur")

        response = client.get(reverse("atenciones-list"))
        assert response.status_code == status.HTTP_200_OK

        results = response.data
        if isinstance(results, dict) and "results" in results:
            results = results["results"]
        row = next(r for r in results if r["id"] == atencion.id)
        turno_paciente = (row.get("turno") or {}).get("paciente")
        _assert_paciente_liviano(turno_paciente)
