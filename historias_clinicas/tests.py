from django.test import TestCase
from .models import HistoriaClinica, Consulta, Sintoma, Diagnostico, Tratamiento
from pacientes.models import Paciente
from medicos.models import Medico
from turnos.models import Turno
from django.utils import timezone

class SintomaModelTest(TestCase):
    def test_creacion_sintoma(self):
        sintoma = Sintoma.objects.create(nombre="Fiebre")
        self.assertEqual(str(sintoma), "Fiebre")

# Puedes agregar más tests para los otros modelos siguiendo este ejemplo.
