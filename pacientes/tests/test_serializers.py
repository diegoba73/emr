"""Tests del serializer de ``Paciente``."""
import pytest

from pacientes.models import Paciente
from pacientes.serializers import PacienteLightSerializer, PacienteSerializer


@pytest.mark.django_db
class TestPacienteSerializerNormalizacion:
    def test_normaliza_nombre_y_apellido(self):
        serializer = PacienteSerializer(
            data={"dni": "SER-NRM-0", "nombre": "  juan  ", "apellido": "  perez  "}
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.nombre == "Juan"
        assert instance.apellido == "Perez"

    def test_acepta_nombre_y_apellido_none(self):
        serializer = PacienteSerializer(
            data={"dni": "SER-NRM-1", "nombre": None, "apellido": None}
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.nombre is None
        assert instance.apellido is None

    def test_dni_obligatorio(self):
        serializer = PacienteSerializer(data={"dni": "   ", "nombre": "X"})
        assert not serializer.is_valid()
        assert "dni" in serializer.errors


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
