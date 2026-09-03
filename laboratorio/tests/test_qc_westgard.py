"""Evaluación Westgard: historial y re-run tras rechazo."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_qc import CorridaQC, LoteControl, MaterialControl
from laboratorio.qc_service import evaluar_y_guardar_punto, finalizar_corrida
from laboratorio.qc_westgard import evaluate_punto


class TestEvaluatePuntoUnit(TestCase):
    def test_r4s_con_historial_rechaza(self):
        # z prev = -5, z nuevo = -1 → Δ = 4 → R-4s
        result = evaluate_punto(190, mean=200, sd=10, previous_puntos=[{"valor": 150, "z": -5.0}])
        self.assertIn("R-4s", result["rules"])
        self.assertTrue(result["fuera_control"])

    def test_dentro_2s_sin_historial_ok(self):
        result = evaluate_punto(190, mean=200, sd=10, previous_puntos=[])
        self.assertFalse(result["fuera_control"])
        self.assertEqual(result["rules"], [])


class TestRerunTrasRechazo(TestCase):
    def setUp(self):
        muestra = TipoMuestra.objects.create(codigo="SANGRE_WG", nombre="Sangre WG")
        examen = TipoExamen.objects.create(
            codigo="GLU_WG",
            nombre="Glucosa WG",
            tipo_muestra_requerida=muestra,
            tipo_resultado="NUMERICO",
        )
        self.mat = MaterialControl.objects.create(
            nombre="Ctrl GLU S2",
            nivel=MaterialControl.Nivel.N2,
            tipo_examen=examen,
            media_target=Decimal("200"),
            de_target=Decimal("10"),
            activo=True,
        )
        self.lote = LoteControl.objects.create(
            material=self.mat,
            codigo_lote="L-WG",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )

    def _nueva_corrida(self):
        return CorridaQC.objects.create(
            lote_control=self.lote,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.PENDIENTE,
        )

    def test_rerun_en_rango_no_dispara_r4s_contra_rechazado(self):
        """Caso UI: 150 rechazado (1-3s) y luego 190 en ±2s debe aceptar."""
        c1 = self._nueva_corrida()
        p1 = evaluar_y_guardar_punto(c1, Decimal("150"))
        finalizar_corrida(c1)
        c1.refresh_from_db()
        self.assertTrue(p1.fuera_control)
        self.assertEqual(c1.estado, CorridaQC.Estado.RECHAZADA)
        self.assertIn("1-3s", p1.reglas_disparadas)

        c2 = self._nueva_corrida()
        p2 = evaluar_y_guardar_punto(c2, Decimal("190"))
        finalizar_corrida(c2)
        c2.refresh_from_db()
        self.assertFalse(p2.fuera_control)
        self.assertNotIn("R-4s", p2.reglas_disparadas or [])
        self.assertEqual(c2.estado, CorridaQC.Estado.ACEPTADA)
