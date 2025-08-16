from django.test import TestCase
from .models import Medico, Especialidad

class EspecialidadModelTest(TestCase):
    def test_creacion_especialidad(self):
        esp = Especialidad.objects.create(nombre="Cardiología")
        self.assertEqual(str(esp), "Cardiología")

# Puedes agregar más tests para los otros modelos siguiendo este ejemplo.
