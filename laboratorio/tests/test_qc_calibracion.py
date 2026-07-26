"""Validación de calibración QC (punto único vs curva multipunto)."""
from datetime import date, timedelta

from django.test import TestCase

from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_qc import Calibracion, EquipoAnalizador
from laboratorio.serializers_qc import CalibracionSerializer


class TestCalibracionSerializer(TestCase):
    def setUp(self):
        self.muestra = TipoMuestra.objects.create(codigo="SANGRE_QC", nombre="Sangre QC")
        self.examen = TipoExamen.objects.create(
            codigo="PCR_QC",
            nombre="PCR test QC",
            tipo_muestra_requerida=self.muestra,
            tipo_resultado="NUMERICO",
        )
        self.equipo = EquipoAnalizador.objects.create(
            codigo="CM260_T",
            nombre="CM260 test",
            marca_modelo="CM260",
        )
        self.base = {
            "equipo": self.equipo.id,
            "fecha": date.today().isoformat(),
            "vigente_hasta": (date.today() + timedelta(days=30)).isoformat(),
            "calibrador_nombre": "Calibrador A Plus",
            "marca": "Wiener",
            "codigo_lote": "L1",
        }

    def test_punto_unico_ok(self):
        ser = CalibracionSerializer(
            data={**self.base, "tipo": Calibracion.Tipo.PUNTO_UNICO, "puntos_curva": []}
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        obj = ser.save()
        self.assertEqual(obj.tipo, Calibracion.Tipo.PUNTO_UNICO)

    def test_curva_sin_examen_falla(self):
        ser = CalibracionSerializer(
            data={
                **self.base,
                "tipo": Calibracion.Tipo.CURVA_MULTIPUNTO,
                "puntos_curva": [
                    {"orden": 1, "concentracion": "0", "senal": "0.1"},
                    {"orden": 2, "concentracion": "10", "senal": "0.5"},
                ],
            }
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("tipo_examen", ser.errors)

    def test_curva_pocos_puntos_falla(self):
        ser = CalibracionSerializer(
            data={
                **self.base,
                "tipo": Calibracion.Tipo.CURVA_MULTIPUNTO,
                "tipo_examen": self.examen.id,
                "puntos_curva": [{"orden": 1, "concentracion": "0", "senal": "0.1"}],
            }
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("puntos_curva", ser.errors)

    def test_curva_ok(self):
        ser = CalibracionSerializer(
            data={
                **self.base,
                "tipo": Calibracion.Tipo.CURVA_MULTIPUNTO,
                "tipo_examen": self.examen.id,
                "calibrador_nombre": "Curva PCR",
                "puntos_curva": [
                    {"orden": 1, "concentracion": "0", "senal": "0.01", "unidad": "mg/L"},
                    {"orden": 2, "concentracion": "20", "senal": "0.40", "unidad": "mg/L"},
                ],
            }
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        obj = ser.save()
        self.assertEqual(obj.tipo_examen_id, self.examen.id)
        self.assertEqual(len(obj.puntos_curva), 2)
