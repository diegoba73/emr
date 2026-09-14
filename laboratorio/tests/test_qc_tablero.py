"""Tablero IQC de la mañana y materiales canónicos (sin duplicados)."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

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
    PuntoQC,
)
from laboratorio.qc_service import estado_iqc_solicitud
from laboratorio.qc_tablero import es_dia_aviso_control_valores, tablero_iqc_hoy
from laboratorio.equipos_lab import codigo_equipo_canonico, es_equipo_valores_a_demanda
from laboratorio.tests.test_qc_gate import _FakeSolicitud

User = get_user_model()

# 2026-09-07 = lunes, 2026-09-08 = martes, 2026-09-11 = viernes
LUNES = date(2026, 9, 7)
MARTES = date(2026, 9, 8)
VIERNES = date(2026, 9, 11)


class TestEquiposCanonico(TestCase):
    def test_diestro_alias_ec90(self):
        self.assertEqual(codigo_equipo_canonico("DIESTRO"), "ERBA_EC90")
        self.assertEqual(codigo_equipo_canonico("EC90"), "ERBA_EC90")
        self.assertTrue(es_equipo_valores_a_demanda("VIDAS_KUBE"))
        self.assertTrue(es_equipo_valores_a_demanda("FINECARE"))
        self.assertTrue(es_equipo_valores_a_demanda("EDAN_I15"))
        self.assertFalse(es_equipo_valores_a_demanda("CM260"))
        self.assertFalse(es_equipo_valores_a_demanda("ERBA_EC90"))


def _aware(d: date, t: time | None = None):
    return timezone.make_aware(datetime.combine(d, t or time(10, 0)))


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

    def _corridas_ok_rapido(self, dia: date):
        for nivel in (CorridaQC.Nivel.N1, CorridaQC.Nivel.N2):
            CorridaQC.objects.create(
                lote_producto=self.lote,
                equipo=self.cm260,
                nivel=nivel,
                fecha=_aware(dia),
                estado=CorridaQC.Estado.ACEPTADA,
            )

    def test_es_dia_aviso_lun_vie(self):
        self.assertTrue(es_dia_aviso_control_valores(fecha=LUNES))
        self.assertTrue(es_dia_aviso_control_valores(fecha=VIERNES))
        self.assertFalse(es_dia_aviso_control_valores(fecha=MARTES))

    def test_aviso_valores_lunes_sin_puntos(self):
        self._corridas_ok_rapido(LUNES)
        with patch("django.utils.timezone.localdate", return_value=LUNES):
            data = tablero_iqc_hoy()
            card = next(e for e in data["equipos"] if e["codigo"] == "CM260")
        self.assertTrue(data["dia_aviso_control_valores"])
        self.assertEqual(card["estado"], "liberado")
        self.assertTrue(card["aviso_valores"])
        self.assertFalse(card["s1"]["con_valores"])
        self.assertFalse(card["s2"]["con_valores"])
        self.assertTrue(any(a["codigo"] == "CM260" for a in data["avisos_valores"]))

    def test_aviso_valores_se_limpia_con_puntos(self):
        self._corridas_ok_rapido(LUNES)
        for c in CorridaQC.objects.filter(lote_producto=self.lote):
            PuntoQC.objects.create(corrida=c, tipo_examen=self.glu, valor=Decimal("100"))
        with patch("django.utils.timezone.localdate", return_value=LUNES):
            card = next(e for e in tablero_iqc_hoy()["equipos"] if e["codigo"] == "CM260")
        self.assertFalse(card["aviso_valores"])
        self.assertTrue(card["s1"]["con_valores"])
        self.assertTrue(card["s2"]["con_valores"])

    def test_sin_aviso_valores_martes(self):
        self._corridas_ok_rapido(MARTES)
        with patch("django.utils.timezone.localdate", return_value=MARTES):
            data = tablero_iqc_hoy()
            card = next(e for e in data["equipos"] if e["codigo"] == "CM260")
        self.assertFalse(data["dia_aviso_control_valores"])
        self.assertFalse(card["aviso_valores"])
        self.assertEqual(card["estado"], "liberado")

    def test_aviso_valores_viernes_endpoint(self):
        self._corridas_ok_rapido(VIERNES)
        with patch("django.utils.timezone.localdate", return_value=VIERNES):
            resp = self.client.get("/api/lab/qc/tablero-hoy/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data["dia_aviso_control_valores"])
        card = next(e for e in resp.data["equipos"] if e["codigo"] == "CM260")
        self.assertTrue(card["aviso_valores"])
        self.assertEqual(card["politica_valores"], "LUN_VIE")
        self.assertIn("OK rápido", card["aviso_valores_mensaje"])

    def test_vidas_finecare_edan_sin_aviso_lun_vie(self):
        muestra = TipoMuestra.objects.get(codigo="SANGRE_TAB")
        vidas = EquipoAnalizador.objects.create(
            codigo="VIDAS_KUBE", nombre="VIDAS KUBE", activo=True
        )
        fine = EquipoAnalizador.objects.create(codigo="FINECARE", nombre="Finecare", activo=True)
        edan = EquipoAnalizador.objects.create(codigo="EDAN_I15", nombre="EDAN i15", activo=True)

        tsh = TipoExamen.objects.create(
            codigo="TSH",
            nombre="TSH",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=vidas,
        )
        hba = TipoExamen.objects.create(
            codigo="HBA1C",
            nombre="HbA1c",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=fine,
        )
        for mat_eq, exam, nivel in (
            (vidas, tsh, MaterialControl.Nivel.N1),
            (vidas, tsh, MaterialControl.Nivel.N2),
            (fine, hba, MaterialControl.Nivel.N1),
            (fine, hba, MaterialControl.Nivel.N2),
        ):
            MaterialControl.objects.create(
                nombre=f"Ctrl {exam.codigo} {nivel}",
                nivel=nivel,
                tipo_examen=exam,
                equipo=mat_eq,
                media_target=Decimal("100"),
                de_target=Decimal("5"),
                activo=True,
            )
        prod_edan = ProductoControl.objects.create(
            codigo="CTRL_EDAN",
            nombre="Control EDAN",
            equipo=edan,
            modo=ProductoControl.Modo.MULTIPARAM,
            activo=True,
        )
        LoteProductoControl.objects.create(
            producto=prod_edan,
            codigo_lote="ED1",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        with patch("django.utils.timezone.localdate", return_value=LUNES):
            data = tablero_iqc_hoy()
        self.assertTrue(data["dia_aviso_control_valores"])
        for codigo in ("VIDAS_KUBE", "FINECARE", "EDAN_I15"):
            card = next(e for e in data["equipos"] if e["codigo"] == codigo)
            self.assertEqual(card["politica_valores"], "A_DEMANDA", codigo)
            self.assertFalse(card["aviso_valores"], codigo)
        self.assertFalse(any(a["codigo"] in {"VIDAS_KUBE", "FINECARE", "EDAN_I15"} for a in data["avisos_valores"]))
        cm = next(e for e in data["equipos"] if e["codigo"] == "CM260")
        self.assertEqual(cm["politica_valores"], "LUN_VIE")
