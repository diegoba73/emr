"""Tests sugerencia de interpretación de orden (sin red MedGemma)."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.sugerir_interpretacion import sugerir_interpretacion_orden
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestSugerirInterpretacion(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="med_interp", password="x", rol="medico")
        self.lab = User.objects.create_user(username="lab_interp", password="x", rol="laboratorio")
        self.pac = Paciente.objects.create(dni="INTP001", nombre="P", apellido="I")
        self.tm = TipoMuestra.objects.create(codigo="SANGRE_I", nombre="Sangre", activo=True)
        self.te = TipoExamen.objects.create(
            codigo="GLU",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        ResultadoExamen.objects.create(
            solicitud=self.sol,
            tipo_examen=self.te,
            valor_obtenido="180",
            valor_numerico=Decimal("180"),
            rango_min_snapshot=Decimal("70"),
            rango_max_snapshot=Decimal("100"),
            es_patologico=True,
        )

    def test_reglas_sin_medgemma(self):
        data = sugerir_interpretacion_orden(self.sol, prefer_medgemma=False)
        self.assertEqual(data["fuente"], "reglas")
        self.assertTrue(data["marcado_sugerencia"])
        self.assertIn("GLU", data["texto"])
        self.assertGreaterEqual(data["total_analizados"], 1)

    def test_api_no_persiste(self):
        client = APIClient()
        client.force_authenticate(user=self.lab)
        obs_antes = self.sol.observaciones
        r = client.post(
            f"/api/lab/solicitudes/{self.sol.id}/sugerir-interpretacion/",
            {"prefer_medgemma": False},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["fuente"], "reglas")
        self.sol.refresh_from_db()
        self.assertEqual(self.sol.observaciones, obs_antes)
