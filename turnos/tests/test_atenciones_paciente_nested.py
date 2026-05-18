"""Contrato de exposición de ``paciente`` anidado en ``GET /api/atenciones/`` (C5.2)."""
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
        "alergias",
        "medicacion_actual",
    }
)

_REQUIRED_PACIENTE_KEYS = frozenset(
    {"id", "dni", "nombre", "apellido", "fecha_nacimiento"}
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

        paciente = Paciente.objects.create(
            dni="NST-RET-001",
            nombre="Ana",
            apellido="Nested",
            fecha_nacimiento=date(1985, 6, 10),
            user=portal_user,
            antecedentes_personales="Antecedente secreto",
            antecedentes_familiares="Familiar secreto",
            observaciones="Observación secreta",
            creado_por=creator,
            modificado_por=creator,
        )
        recurso = Recurso.objects.create(
            nombre="Cons Nested",
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
        )
        atencion = Atencion.objects.create(
            turno=turno,
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
        )

        response = client.get(reverse("atenciones-detail", kwargs={"pk": atencion.pk}))
        assert response.status_code == status.HTTP_200_OK, response.data

        paciente_data = response.data["paciente"]
        assert paciente_data is not None
        assert _FORBIDDEN_PACIENTE_KEYS.isdisjoint(paciente_data.keys())
        assert _REQUIRED_PACIENTE_KEYS.issubset(paciente_data.keys())
        assert paciente_data["dni"] == "NST-RET-001"

    def test_list_paciente_anidado_liviano(self):
        client, _, medico = _medico_client("list")
        paciente = Paciente.objects.create(
            dni="NST-LST-001",
            nombre="List",
            apellido="Nested",
            fecha_nacimiento=date(1990, 1, 1),
            antecedentes_personales="No debe filtrarse",
            observaciones="Tampoco",
        )
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
        paciente_data = row["paciente"]
        assert _FORBIDDEN_PACIENTE_KEYS.isdisjoint(paciente_data.keys())
        assert _REQUIRED_PACIENTE_KEYS.issubset(paciente_data.keys())

    def test_turno_paciente_puede_seguir_con_exposicion_legacy(self):
        """C5.3: ``turno.paciente`` aún usa ``api.TurnoSerializer`` con ``PacienteSerializer`` legacy."""
        client, _, medico = _medico_client("turno-debt")
        paciente = Paciente.objects.create(
            dni="NST-TUR-001",
            nombre="Turno",
            apellido="Debt",
            fecha_nacimiento=date(1991, 2, 2),
            antecedentes_personales="Solo en turno anidado por ahora",
        )
        recurso = Recurso.objects.create(
            nombre="Cons Turno Debt",
            ubicacion="P2",
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )
        turno = Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=timezone.now() + timedelta(hours=3),
            fecha_hora_fin=timezone.now() + timedelta(hours=4),
            estado="CONFIRMADO",
        )
        atencion = Atencion.objects.create(
            turno=turno,
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
        )

        response = client.get(reverse("atenciones-detail", kwargs={"pk": atencion.pk}))
        assert response.status_code == status.HTTP_200_OK

        top = response.data["paciente"]
        assert "antecedentes_personales" not in top

        turno_block = response.data.get("turno") or {}
        turno_paciente = (turno_block or {}).get("paciente") or {}
        if turno_paciente:
            assert "antecedentes_personales" in turno_paciente
