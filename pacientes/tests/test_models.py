"""Tests del modelo ``Paciente``.

Cubren el cálculo de ``edad`` (caso normal, bordes y futuro), el comportamiento
de ``nombre_completo`` (incluido el caso con valores ``None``) y la unicidad
de ``dni``.
"""
from datetime import date, timedelta

import pytest

from pacientes.models import Paciente


@pytest.mark.django_db
class TestPacienteEdad:
    """Cálculo de la propiedad ``edad``."""

    def test_edad_paciente_nacido_hace_exactamente_20_anos(self):
        hoy = date.today()
        try:
            fecha_nacimiento = date(hoy.year - 20, hoy.month, hoy.day)
        except ValueError:
            # 29 de febrero en año no bisiesto: se ajusta al 28 para el test.
            fecha_nacimiento = date(hoy.year - 20, hoy.month, hoy.day - 1)

        paciente = Paciente.objects.create(
            dni="ED-20-0",
            nombre="Juan",
            apellido="Pérez",
            fecha_nacimiento=fecha_nacimiento,
        )

        assert paciente.edad == 20

    def test_edad_paciente_le_falta_un_dia_para_cumplir_20(self):
        """Borde correcto: alguien al que le falta 1 día para cumplir 20 años
        todavía tiene 19. Esto se modela como una fecha de nacimiento un día
        posterior al cumpleaños teórico de hace 20 años.
        """
        hoy = date.today()
        try:
            base = date(hoy.year - 20, hoy.month, hoy.day)
        except ValueError:
            base = date(hoy.year - 20, hoy.month, hoy.day - 1)
        fecha_nacimiento = base + timedelta(days=1)

        paciente = Paciente.objects.create(
            dni="ED-19-1",
            nombre="María",
            apellido="González",
            fecha_nacimiento=fecha_nacimiento,
        )

        assert paciente.edad == 19

    def test_edad_paciente_nacido_en_el_futuro(self):
        """Caso borde: fecha en el futuro produce edad <= 0 (no es ``None``)."""
        fecha_nacimiento = date.today() + timedelta(days=1)
        paciente = Paciente.objects.create(
            dni="ED-FUT-1",
            nombre="Carlos",
            apellido="López",
            fecha_nacimiento=fecha_nacimiento,
        )
        edad = paciente.edad
        assert edad is not None
        assert edad <= 0

    def test_edad_paciente_sin_fecha_nacimiento(self):
        paciente = Paciente.objects.create(
            dni="ED-NONE-0",
            nombre="Ana",
            apellido="Martínez",
        )
        assert paciente.edad is None


@pytest.mark.django_db
class TestPacienteNombreCompleto:
    """Comportamiento de ``nombre_completo`` con datos parciales."""

    def test_nombre_completo_con_nombre_y_apellido(self):
        paciente = Paciente.objects.create(
            dni="NC-OK-0",
            nombre="Pedro",
            apellido="Sánchez",
        )
        assert paciente.nombre_completo == "Pedro Sánchez"

    def test_nombre_completo_solo_apellido(self):
        paciente = Paciente.objects.create(
            dni="NC-OK-1",
            apellido="Sánchez",
        )
        assert paciente.nombre_completo == "Sánchez"

    def test_nombre_completo_solo_nombre(self):
        paciente = Paciente.objects.create(
            dni="NC-OK-2",
            nombre="Pedro",
        )
        assert paciente.nombre_completo == "Pedro"

    def test_nombre_completo_sin_nombre_ni_apellido_devuelve_dni(self):
        """Bug fix: con ``nombre=None`` y ``apellido=None`` no debe devolver
        la cadena literal ``"None None"`` sino el fallback ``"Paciente {dni}"``.
        """
        paciente = Paciente.objects.create(dni="NC-NONE-0")
        assert paciente.nombre_completo == "Paciente NC-NONE-0"

    def test_nombre_completo_con_strings_vacios_devuelve_dni(self):
        paciente = Paciente.objects.create(
            dni="NC-EMPTY-0",
            nombre="",
            apellido="",
        )
        assert paciente.nombre_completo == "Paciente NC-EMPTY-0"


@pytest.mark.django_db
class TestPacienteIntegrity:
    def test_dni_unique_constraint(self):
        Paciente.objects.create(dni="UQ-001", nombre="Test", apellido="User")
        with pytest.raises(Exception):
            Paciente.objects.create(dni="UQ-001", nombre="Otro", apellido="Usuario")

    def test_user_es_opcional(self):
        """``Paciente.user`` debe ser opcional (``SET_NULL``, ``null=True``)."""
        paciente = Paciente.objects.create(dni="USR-OPT-0", nombre="Sin", apellido="Usuario")
        assert paciente.user is None
        assert paciente.pk is not None
