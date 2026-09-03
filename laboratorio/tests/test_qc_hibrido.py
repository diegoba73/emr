"""QC híbrido: producto multiparámetro (S1+S2) vs material por ensayo."""
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
    TargetLoteControl,
)
from laboratorio.qc_service import QcGateError, estado_iqc_solicitud, validar_qc_para_cierre
from laboratorio.tests.test_qc_gate import _FakeSolicitud

User = get_user_model()


class TestGateMultiparamStandatrol(TestCase):
    """Orden GLU+UREA exige S1+S2 del producto, no un material por ensayo."""

    def setUp(self):
        self.muestra = TipoMuestra.objects.create(codigo="SANGRE_HY", nombre="Sangre HY")
        self.cm260 = EquipoAnalizador.objects.create(
            codigo="CM260", nombre="CM260", activo=True
        )
        self.glu = TipoExamen.objects.create(
            codigo="GLU",
            nombre="Glucosa",
            tipo_muestra_requerida=self.muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.cm260,
        )
        self.urea = TipoExamen.objects.create(
            codigo="UREA",
            nombre="Urea",
            tipo_muestra_requerida=self.muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.cm260,
        )
        self.producto = ProductoControl.objects.create(
            codigo="STANDATROL_SE",
            nombre="Standatrol S-E 2 Niveles",
            marca="Wiener",
            equipo=self.cm260,
            modo=ProductoControl.Modo.MULTIPARAM,
            activo=True,
        )
        self.lote = LoteProductoControl.objects.create(
            producto=self.producto,
            codigo_lote="L-STA",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        for exam in (self.glu, self.urea):
            for nivel, media, de in (
                (TargetLoteControl.Nivel.N1, Decimal("100"), Decimal("5")),
                (TargetLoteControl.Nivel.N2, Decimal("200"), Decimal("10")),
            ):
                TargetLoteControl.objects.create(
                    lote=self.lote, tipo_examen=exam, nivel=nivel, media_target=media, de_target=de
                )
        # Materiales legado inactivos no deben disparar el gate
        mat = MaterialControl.objects.create(
            nombre="Ctrl GLU legado",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=self.glu,
            equipo=self.cm260,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=False,
        )
        LoteControl.objects.create(
            material=mat,
            codigo_lote="L-LEG",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        self.solicitud = _FakeSolicitud([self.glu.id, self.urea.id])

    def _aceptar_nivel(self, nivel, minutes_ago=0):
        return CorridaQC.objects.create(
            lote_producto=self.lote,
            nivel=nivel,
            equipo=self.cm260,
            fecha=timezone.now() - timedelta(minutes=minutes_ago),
            estado=CorridaQC.Estado.ACEPTADA,
            observaciones="aceptación rápida de nivel",
        )

    def test_sin_corrida_exige_s1_s2_producto_no_por_ensayo(self):
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        msg = str(ctx.exception)
        self.assertIn("Standatrol", msg)
        self.assertIn("S1", msg)
        self.assertIn("S2", msg)
        self.assertIn("CM260", msg)
        self.assertNotIn("GLU S1", msg)
        self.assertNotIn("UREA", msg)

    def test_solo_s1_no_alcanza(self):
        self._aceptar_nivel(CorridaQC.Nivel.N1)
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("S2", str(ctx.exception))

    def test_s1_y_s2_aceptados_habilitan(self):
        self._aceptar_nivel(CorridaQC.Nivel.N1, minutes_ago=10)
        self._aceptar_nivel(CorridaQC.Nivel.N2, minutes_ago=5)
        validar_qc_para_cierre(self.solicitud)
        st = estado_iqc_solicitud(self.solicitud)
        self.assertTrue(st["ok"])
        self.assertTrue(st["aplicable"])


class TestGateVidasPorEnsayo(TestCase):
    def setUp(self):
        muestra = TipoMuestra.objects.create(codigo="SANGRE_VID", nombre="Sangre VID")
        self.vidas = EquipoAnalizador.objects.create(
            codigo="VIDAS_KUBE", nombre="VIDAS KUBE", activo=True
        )
        self.tsh = TipoExamen.objects.create(
            codigo="TSH",
            nombre="TSH",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.vidas,
        )
        self.mat = MaterialControl.objects.create(
            nombre="Ctrl TSH S1",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=self.tsh,
            equipo=self.vidas,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=True,
        )
        self.lote = LoteControl.objects.create(
            material=self.mat,
            codigo_lote="L-TSH",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        self.solicitud = _FakeSolicitud([self.tsh.id])

    def test_tsh_exige_material_vidas(self):
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("TSH", str(ctx.exception))
        self.assertIn("VIDAS_KUBE", str(ctx.exception))

    def test_corrida_material_habilita(self):
        CorridaQC.objects.create(
            lote_control=self.lote,
            equipo=self.vidas,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.ACEPTADA,
        )
        validar_qc_para_cierre(self.solicitud)


class TestGateFinecarePorEnsayo(TestCase):
    def test_hba1c_sigue_por_ensayo(self):
        muestra = TipoMuestra.objects.create(codigo="SANGRE_FC", nombre="Sangre FC")
        finecare = EquipoAnalizador.objects.create(
            codigo="FINECARE", nombre="Finecare", activo=True
        )
        hba = TipoExamen.objects.create(
            codigo="HBA1C",
            nombre="HbA1c",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=finecare,
        )
        mat = MaterialControl.objects.create(
            nombre="Ctrl HBA1C S1",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=hba,
            equipo=finecare,
            media_target=Decimal("5"),
            de_target=Decimal("0.3"),
            activo=True,
        )
        lote = LoteControl.objects.create(
            material=mat,
            codigo_lote="L-HBA",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        fake = _FakeSolicitud([hba.id])
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(fake)
        self.assertIn("HBA1C", str(ctx.exception))
        self.assertIn("FINECARE", str(ctx.exception))
        CorridaQC.objects.create(
            lote_control=lote,
            equipo=finecare,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.ACEPTADA,
        )
        validar_qc_para_cierre(fake)


class TestCorridasHibridasApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="lab_hyb",
            email="lab-hyb@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        muestra = TipoMuestra.objects.create(codigo="SANGRE_API", nombre="Sangre API")
        self.cm260 = EquipoAnalizador.objects.create(
            codigo="CM260", nombre="CM260", activo=True
        )
        self.glu = TipoExamen.objects.create(
            codigo="GLU",
            nombre="Glucosa",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.cm260,
        )
        self.producto = ProductoControl.objects.create(
            codigo="STANDATROL_SE",
            nombre="Standatrol S-E 2 Niveles",
            equipo=self.cm260,
            modo=ProductoControl.Modo.MULTIPARAM,
            activo=True,
        )
        self.lote = LoteProductoControl.objects.create(
            producto=self.producto,
            codigo_lote="L-API",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        TargetLoteControl.objects.create(
            lote=self.lote,
            tipo_examen=self.glu,
            nivel=TargetLoteControl.Nivel.N1,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
        )
        TargetLoteControl.objects.create(
            lote=self.lote,
            tipo_examen=self.glu,
            nivel=TargetLoteControl.Nivel.N2,
            media_target=Decimal("200"),
            de_target=Decimal("10"),
        )
        self.solicitud = _FakeSolicitud([self.glu.id])

    def test_aceptar_nivel_habilita_ese_nivel(self):
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
        self.assertEqual(r.data["estado"], "ACEPTADA")
        self.assertIn("aceptación rápida", (r.data.get("observaciones") or "").lower())
        # Falta S2
        with self.assertRaises(QcGateError):
            validar_qc_para_cierre(self.solicitud)
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
        validar_qc_para_cierre(self.solicitud)

    def test_valores_1_3s_rechaza_nivel(self):
        r = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_producto": self.lote.id,
                "nivel": "N2",
                "modo": "VALORES",
                "fecha": timezone.now().isoformat(),
                "valores": [{"tipo_examen": self.glu.id, "valor": "150"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["estado"], "RECHAZADA")
        puntos = r.data.get("puntos") or []
        self.assertTrue(puntos)
        self.assertTrue(puntos[0]["fuera_control"])
        self.assertIn("1-3s", puntos[0].get("reglas_disparadas") or [])
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("rechazado", str(ctx.exception).lower())

    def test_valores_en_rango_acepta(self):
        r = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_producto": self.lote.id,
                "nivel": "N1",
                "modo": "VALORES",
                "fecha": timezone.now().isoformat(),
                "valores": [{"tipo_examen": self.glu.id, "valor": "100"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["estado"], "ACEPTADA")
