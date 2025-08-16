from django.test import TestCase
from .models import TipoExamen, PanelExamen, SolicitudExamen, ResultadoExamen
from pacientes.models import Paciente
from medicos.models import Medico
from historias_clinicas.models import Consulta

class TipoExamenModelTest(TestCase):
    def test_creacion_tipo_examen(self):
        tipo = TipoExamen.objects.create(nombre="Glucosa")
        self.assertIn("Glucosa", str(tipo))

# Puedes agregar más tests para los otros modelos siguiendo este ejemplo.
