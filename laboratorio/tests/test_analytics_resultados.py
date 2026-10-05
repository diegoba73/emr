"""Tests analítica poblacional (agregados, sin PHI)."""
from datetime import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from laboratorio.analytics_resultados import analytics_analitos
from laboratorio.labwin_firebird_scope import DEFAULT_SCALE_UNTIL
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestAnalyticsResultados(TestCase):
    def setUp(self):
        self.lab = User.objects.create_user(username="lab_an", password="x", rol="laboratorio")
        self.med = User.objects.create_user(username="med_an", password="x", rol="medico")
        self.pac = Paciente.objects.create(dni="ANL001", nombre="A", apellido="N")
        self.tm = TipoMuestra.objects.create(codigo="SANGRE_AN", nombre="Sangre", activo=True)
        self.te = TipoExamen.objects.create(
            codigo="UREA",
            nombre="Urea",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        aware = timezone.is_aware(timezone.now())
        f1 = datetime(2026, 9, 20, 10, 0, 0)
        f2 = datetime(2026, 10, 1, 10, 0, 0)
        if aware:
            f1 = timezone.make_aware(f1)
            f2 = timezone.make_aware(f2)

        # Crear en EN_PROCESO (no se puede agregar ResultadoExamen a FINALIZADO)
        self.sol_in = SolicitudExamen.objects.create(
            paciente=self.pac,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
            numero="LW-2026-88001",
        )
        self.sol_out = SolicitudExamen.objects.create(
            paciente=self.pac,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
            numero="LAB-POST-001",
        )
        ResultadoExamen.objects.create(
            solicitud=self.sol_in,
            tipo_examen=self.te,
            valor_obtenido="40",
            valor_numerico=Decimal("40"),
            es_patologico=False,
        )
        ResultadoExamen.objects.create(
            solicitud=self.sol_out,
            tipo_examen=self.te,
            valor_obtenido="50",
            valor_numerico=Decimal("50"),
            es_patologico=True,
        )
        # auto_now_add + estado final: fijar vía update
        SolicitudExamen.objects.filter(pk=self.sol_in.pk).update(
            fecha_solicitud=f1, estado="FINALIZADO"
        )
        SolicitudExamen.objects.filter(pk=self.sol_out.pk).update(
            fecha_solicitud=f2, estado="FINALIZADO"
        )
        self.sol_in.refresh_from_db()
        self.sol_out.refresh_from_db()

    def test_default_hasta_excluye_post_corte(self):
        data = analytics_analitos(codigo="UREA")
        self.assertEqual(data["hasta"], DEFAULT_SCALE_UNTIL.isoformat())
        self.assertEqual(len(data["analitos"]), 1)
        self.assertEqual(data["analitos"][0]["n"], 1)
        self.assertEqual(data["analitos"][0]["n_labwin"], 1)
        self.assertNotIn("paciente", str(data).lower())

    def test_api_lab_ok_medico_forbidden(self):
        client = APIClient()
        client.force_authenticate(user=self.lab)
        r = client.get("/api/lab/analytics/analitos/", {"codigo": "UREA"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["sin_phi"])

        client.force_authenticate(user=self.med)
        r2 = client.get("/api/lab/analytics/analitos/", {"codigo": "UREA"})
        self.assertEqual(r2.status_code, 403)
