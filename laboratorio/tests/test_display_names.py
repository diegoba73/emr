"""Tests del formato unificado de nombres LIMS."""
import pytest

from laboratorio.display_names import format_apellido_nombre, format_medico_display


class _Persona:
    def __init__(self, apellido="", nombre="", nombre_completo=None):
        self.apellido = apellido
        self.nombre = nombre
        self.nombre_completo = nombre_completo


@pytest.mark.parametrize(
    "apellido,nombre,expected",
    [
        ("Garcia", "Lopez Federico", "Garcia, Lopez Federico"),
        ("Garcia", "", "Garcia"),
        ("", "Ana", "Ana"),
    ],
)
def test_format_apellido_nombre(apellido, nombre, expected):
    assert format_apellido_nombre(_Persona(apellido, nombre)) == expected


def test_format_medico_display_interno():
    assert (
        format_medico_display(_Persona("Ingaramo", "Roberto Antonio"))
        == "Dr. Ingaramo, Roberto Antonio"
    )


def test_format_medico_display_strips_titulo_en_nombre():
    assert (
        format_medico_display(_Persona("García", "Dr. Carlos"))
        == "Dr. García, Carlos"
    )
    assert (
        format_medico_display(_Persona("López", "Dra. María"))
        == "Dr. López, María"
    )


def test_format_medico_display_externo():
    assert (
        format_medico_display(None, externo_nombre="Dr. Externo")
        == "Dr. Externo"
    )


def test_format_medico_display_sin_medico():
    assert format_medico_display(None) == "Sin médico asignado"
