from django.test import TestCase
from .models import Paciente

class PacienteModelTest(TestCase):
    def test_creacion_paciente(self):
        paciente = Paciente.objects.create(nombre="Juan", apellido="Pérez", fecha_nacimiento="2000-01-01", sexo="M", dni="12345678")
        self.assertIn("Pérez", str(paciente))

# Puedes agregar más tests para los otros modelos siguiendo este ejemplo.
