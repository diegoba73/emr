from django.test import TestCase
from .models import Turno
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from datetime import datetime

class TurnoModelTest(TestCase):
    def test_creacion_turno(self):
        paciente = Paciente.objects.create(nombre="Ana", apellido="García", fecha_nacimiento="1990-01-01", sexo="F", dni="87654321")
        especialidad = Especialidad.objects.create(nombre="Pediatría")
        turno = Turno.objects.create(paciente=paciente, especialidad_turno=especialidad, fecha_hora_inicio="2024-01-01T10:00:00")
        self.assertIn("García", str(turno))

# Puedes agregar más tests para los otros modelos siguiendo este ejemplo.
