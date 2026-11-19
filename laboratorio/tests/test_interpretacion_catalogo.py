"""Validación de campos_detalle / tabla_interpretacion y snapshots al cargar."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from laboratorio.interpretacion_catalogo import (
    normalize_campos_detalle,
    normalize_tabla_interpretacion,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.resultados_clinicos import aplicar_carga_estructurada
from laboratorio.serializers import TipoExamenSerializer
from pacientes.models import Paciente


class TestNormalizeCamposDetalle(TestCase):
    def test_lista_vacia(self):
        self.assertEqual(normalize_campos_detalle([]), [])
        self.assertEqual(normalize_campos_detalle(None), [])

    def test_normaliza_y_omite_vacios(self):
        out = normalize_campos_detalle(
            [
                {"etiqueta": " Alergeno ", "valor": " d201 "},
                {"etiqueta": "", "valor": ""},
            ]
        )
        self.assertEqual(out, [{"etiqueta": "Alergeno", "valor": "d201"}])

    def test_etiqueta_obligatoria_si_hay_valor(self):
        with self.assertRaises(ValidationError):
            normalize_campos_detalle([{"etiqueta": "", "valor": "x"}])


class TestNormalizeTablaInterpretacion(TestCase):
    def test_none_si_vacio(self):
        self.assertIsNone(normalize_tabla_interpretacion(None))
        self.assertIsNone(normalize_tabla_interpretacion({}))

    def test_tabla_valida(self):
        raw = {
            "titulo": "Interpretación",
            "columnas": ["kU/L", "CLASE", "NIVEL"],
            "filas": [
                ["< 0,10", "0", "No detectable"],
                ["0,10 - 0,34", "0", "Muy bajo"],
            ],
        }
        out = normalize_tabla_interpretacion(raw)
        self.assertEqual(out["titulo"], "Interpretación")
        self.assertEqual(len(out["columnas"]), 3)
        self.assertEqual(len(out["filas"]), 2)

    def test_fila_con_columnas_incorrectas(self):
        with self.assertRaises(ValidationError):
            normalize_tabla_interpretacion(
                {
                    "columnas": ["A", "B"],
                    "filas": [["solo_una"]],
                }
            )


@pytest.mark.django_db
class TestTipoExamenSerializerInterpretacion(TestCase):
    def setUp(self):
        self.tm = TipoMuestra.objects.create(codigo="S-INT", nombre="Suero", activo=True)

    def test_serializer_acepta_campos_y_tabla(self):
        ser = TipoExamenSerializer(
            data={
                "codigo": "IGE-BT",
                "nombre": "IgE Blomia",
                "tipo_muestra_requerida": self.tm.pk,
                "campos_detalle": [
                    {"etiqueta": "Alergeno", "valor": "d201 - Blomia tropicalis"}
                ],
                "tabla_interpretacion": {
                    "titulo": "Interpretación",
                    "columnas": ["kU/L", "CLASE"],
                    "filas": [["< 0,10", "0"]],
                },
            }
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        te = ser.save()
        self.assertEqual(te.campos_detalle[0]["etiqueta"], "Alergeno")
        self.assertEqual(te.tabla_interpretacion["columnas"], ["kU/L", "CLASE"])

    def test_serializer_rechaza_tabla_inconsistente(self):
        ser = TipoExamenSerializer(
            data={
                "codigo": "BAD-TAB",
                "nombre": "Bad",
                "tipo_muestra_requerida": self.tm.pk,
                "tabla_interpretacion": {
                    "columnas": ["A", "B", "C"],
                    "filas": [["1", "2"]],
                },
            }
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("tabla_interpretacion", ser.errors)


@pytest.mark.django_db
class TestSnapshotInterpretacion(TestCase):
    def setUp(self):
        self.tm = TipoMuestra.objects.create(codigo="S-SNP", nombre="Suero", activo=True)
        self.te = TipoExamen.objects.create(
            codigo="IGE-SNP",
            nombre="IgE snap",
            tipo_muestra_requerida=self.tm,
            unidad_default="kU/L",
            campos_detalle=[{"etiqueta": "Alergeno", "valor": "d201"}],
            tabla_interpretacion={
                "titulo": "Interpretación",
                "columnas": ["kU/L", "CLASE", "NIVEL"],
                "filas": [["0,10 - 0,34", "0", "Muy bajo"]],
            },
            precio=Decimal("1"),
            activo=True,
        )
        pac = Paciente.objects.create(dni="11223344", nombre="P", apellido="Snap")
        self.sol = SolicitudExamen.objects.create(
            paciente=pac, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO"
        )
        self.res = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te, valor_obtenido=""
        )

    def test_carga_copia_snapshots(self):
        aplicar_carga_estructurada(
            self.res, self.te, {"valor": "0,25", "valor_numerico": "0.25"}
        )
        self.res.save()
        self.res.refresh_from_db()
        self.assertEqual(
            self.res.campos_detalle_snapshot,
            [{"etiqueta": "Alergeno", "valor": "d201"}],
        )
        self.assertEqual(
            self.res.tabla_interpretacion_snapshot["columnas"],
            ["kU/L", "CLASE", "NIVEL"],
        )

    def test_cambio_catalogo_no_altera_snapshot_ya_cargado(self):
        aplicar_carga_estructurada(self.res, self.te, {"valor": "0.25"})
        self.res.save()
        self.te.campos_detalle = [{"etiqueta": "Alergeno", "valor": "OTRO"}]
        self.te.save(update_fields=["campos_detalle"])
        self.res.refresh_from_db()
        self.assertEqual(self.res.campos_detalle_snapshot[0]["valor"], "d201")
