"""Tablero IQC de la mañana y materiales canónicos (sin duplicados)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_qc import (
    CorridaQC,
    EquipoAnalizador,
    LoteControl,
    LoteProductoControl,
    MaterialControl,
    ProductoControl,
)
from laboratorio.qc_service import estado_iqc_solicitud
from laboratorio.qc_tablero import tablero_iqc_hoy
from laboratorio.tests.test_qc_gate import _FakeSolicitud

User = get_user_model()


class TestMaterialesCanonicosGate(TestCase):
    def test_duplicados_sin_equipo_no_bloquean(self):
        muestra = TipoMuestra.objects.create(codigo="SANGRE_DUP", nombre="Sangre DUP")
        fine = EquipoAnalizador.objects.create(codigo="FINECARE", nombre="Finecare", activo=True)
        hba = TipoExamen.objects.create(
            codigo="HBA1C",
            nombre="HbA1c",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=fine,
        )
        for _ in range(3):
            MaterialControl.objects.create(
                nombre="Control VIDAS",
                nivel=MaterialControl.Nivel.N1,
                tipo_examen=hba,
                equipo=None,
                media_target=Decimal("100"),
                de_target=Decimal("5"),
                activo=True,
            )
        bueno = MaterialControl.objects.create(
            nombre="Standatrol HBA1C N1",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=hba,
            equipo=fine,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=True,
        )
        lote = LoteControl.objects.create(
            material=bueno,
            codigo_lote="L1",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        fake = _FakeSolicitud([hba.id])
        st = estado_iqc_solicitud(fake)
        self.assertFalse(st["ok"])
        self.assertEqual(sum(1 for p in st["problemas"] if "HBA1C" in p), 1)
        CorridaQC.objects.create(
            lote_control=lote,
            equipo=fine,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.ACEPTADA,
        )
        st2 = estado_iqc_solicitud(fake)
        self.assertTrue(st2["ok"], st2["problemas"])


class TestTableroHoy(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="lab_tab",
            email="lab-tab@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        muestra = TipoMuestra.objects.create(codigo="SANGRE_TAB", nombre="Sangre TAB")
        self.cm260 = EquipoAnalizador.objects.create(codigo="CM260", nombre="CM260", activo=True)
        self.glu = TipoExamen.objects.create(
            codigo="GLU",
            nombre="Glucosa",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.cm260,
        )
        self.producto = ProductoControl.objects.create(
            codigo="STD01",
            nombre="Standatrol",
            equipo=self.cm260,
            modo=ProductoControl.Modo.MULTIPARAM,
            activo=True,
        )
        self.lote = LoteProductoControl.objects.create(
            producto=self.producto,
            codigo_lote="741",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )

    def test_tablero_cm260_falta_luego_liberado(self):
        data = tablero_iqc_hoy()
        card = next(e for e in data["equipos"] if e["codigo"] == "CM260")
        self.assertEqual(card["modo"], "MULTIPARAM")
        self.assertEqual(card["estado"], "falta")
        self.assertIn("S1", card["resumen"])
        r = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_producto": self.lote.id,
                "nivel": "N1",
                "modo": "ACEPTAR_NIVEL",
                "fecha": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        r2 = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_producto": self.lote.id,
                "nivel": "N2",
                "modo": "ACEPTAR_NIVEL",
                "fecha": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)
        card2 = next(e for e in tablero_iqc_hoy()["equipos"] if e["codigo"] == "CM260")
        self.assertEqual(card2["estado"], "liberado")

    def test_rechazar_y_endpoint(self):
        r = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_producto": self.lote.id,
                "nivel": "N1",
                "modo": "RECHAZAR_NIVEL",
                "fecha": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["estado"], "RECHAZADA")
        resp = self.client.get("/api/lab/qc/tablero-hoy/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        card = next(e for e in resp.data["equipos"] if e["codigo"] == "CM260")
        self.assertEqual(card["estado"], "no_ok")

    def test_aceptar_material_sin_valor(self):
        fine = EquipoAnalizador.objects.create(codigo="FINECARE", nombre="Finecare", activo=True)
        hba = TipoExamen.objects.create(
            codigo="HBA1C",
            nombre="HbA1c",
            tipo_muestra_requerida=TipoMuestra.objects.get(codigo="SANGRE_TAB"),
            tipo_resultado="NUMERICO",
            equipo_analizador=fine,
        )
        mat = MaterialControl.objects.create(
            nombre="Ctrl HBA1C N1",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=hba,
            equipo=fine,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=True,
        )
        lote = LoteControl.objects.create(
            material=mat,
            codigo_lote="FC1",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        r = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_control": lote.id,
                "modo": "ACEPTAR_NIVEL",
                "fecha": timezone.now().isoformat(),
                "equipo": fine.id,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["estado"], "ACEPTADA")
