"""Tests del serializer de ``Paciente``."""
from datetime import date

import pytest

from pacientes.models import Paciente
from pacientes.serializers import PacienteLightSerializer, PacienteSerializer


def _payload_create(**overrides):
    base = {
        "dni": "SER-BASE-0",
        "nombre": "Juan",
        "apellido": "Pérez",
        "fecha_nacimiento": date(1990, 5, 15),
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
class TestPacienteSerializerCreacionIdentidadMinima:
    def test_create_sin_nombre_falla(self):
        data = _payload_create()
        del data["nombre"]
        serializer = PacienteSerializer(data=data)
        assert not serializer.is_valid()
        assert "nombre" in serializer.errors

    def test_create_sin_apellido_falla(self):
        data = _payload_create()
        del data["apellido"]
        serializer = PacienteSerializer(data=data)
        assert not serializer.is_valid()
        assert "apellido" in serializer.errors

    def test_create_sin_fecha_nacimiento_falla(self):
        data = _payload_create()
        del data["fecha_nacimiento"]
        serializer = PacienteSerializer(data=data)
        assert not serializer.is_valid()
        assert "fecha_nacimiento" in serializer.errors

    def test_create_nombre_apellido_vacios_falla(self):
        serializer = PacienteSerializer(
            data=_payload_create(nombre="   ", apellido="  ")
        )
        assert not serializer.is_valid()
        assert "nombre" in serializer.errors
        assert "apellido" in serializer.errors

    def test_create_completo_valido(self):
        serializer = PacienteSerializer(data=_payload_create(dni="SER-OK-0"))
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.dni == "SER-OK-0"
        assert instance.nombre == "Juan"
        assert instance.fecha_nacimiento == date(1990, 5, 15)


@pytest.mark.django_db
class TestPacienteSerializerNormalizacion:
    def test_normaliza_nombre_y_apellido(self):
        serializer = PacienteSerializer(
            data=_payload_create(
                dni="SER-NRM-0",
                nombre="  juan  ",
                apellido="  perez  ",
            )
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.nombre == "Juan"
        assert instance.apellido == "Perez"

    def test_create_rechaza_nombre_y_apellido_none(self):
        """Creación API ya no admite nombre/apellido nulos (legacy solo en BD)."""
        serializer = PacienteSerializer(
            data={
                "dni": "SER-NRM-1",
                "nombre": None,
                "apellido": None,
                "fecha_nacimiento": date(1985, 1, 1),
            }
        )
        assert not serializer.is_valid()
        assert "nombre" in serializer.errors
        assert "apellido" in serializer.errors

    def test_dni_obligatorio(self):
        serializer = PacienteSerializer(
            data={
                "dni": "   ",
                "nombre": "X",
                "apellido": "Y",
                "fecha_nacimiento": date(2000, 1, 1),
            }
        )
        assert not serializer.is_valid()
        assert "dni" in serializer.errors


@pytest.mark.django_db
class TestPacienteSerializerActualizacion:
    def test_partial_update_no_exige_identidad_completa(self):
        paciente = Paciente.objects.create(dni="SER-UPD-0")
        serializer = PacienteSerializer(
            paciente,
            data={"telefono": "111222333"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.telefono == "111222333"

    def test_partial_update_sin_reenviar_fecha_nacimiento(self):
        paciente = Paciente.objects.create(
            dni="SER-UPD-1", nombre="Ana", apellido="López"
        )
        serializer = PacienteSerializer(
            paciente,
            data={"observaciones": "Nota"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        paciente.refresh_from_db()
        assert paciente.observaciones == "Nota"
        assert paciente.fecha_nacimiento is None


@pytest.mark.django_db
class TestPacienteSerializerCamposDerivados:
    def test_expone_nombre_completo_y_edad(self):
        paciente = Paciente.objects.create(
            dni="SER-DRV-0", nombre="Pedro", apellido="Sánchez"
        )
        data = PacienteSerializer(paciente).data
        assert data["nombre_completo"] == "Pedro Sánchez"
        assert "edad" in data

    def test_light_serializer_expone_nombre_completo(self):
        paciente = Paciente.objects.create(dni="SER-DRV-1")
        data = PacienteLightSerializer(paciente).data
        assert data["nombre_completo"] == "Paciente SER-DRV-1"
