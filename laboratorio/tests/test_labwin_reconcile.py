"""Tests del reconciliador LabWin (sin PHI en asserts de valores clínicos)."""
from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from laboratorio.labwin_reconcile import (
    analyze_csv_duplicates_and_patients,
    normalize_valor_comparacion,
    reconcile_orders_against_db,
    stats_as_public_dict,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente

FIXTURE = Path(__file__).parent / "fixtures" / "labwin_min.csv"


class LabwinReconcileNormalizeTests(SimpleTestCase):
    def test_normalize_valor(self):
        self.assertEqual(normalize_valor_comparacion("14,1"), "14.1")
        self.assertEqual(normalize_valor_comparacion("------------"), "")
        self.assertEqual(normalize_valor_comparacion("  75 "), "75")


class LabwinReconcileCsvOnlyTests(SimpleTestCase):
    def test_fixture_patients_without_orders_and_dups(self):
        stats = analyze_csv_duplicates_and_patients(FIXTURE)
        # Fixture: SKIP_DNI omite una fila; pacientes con orden < únicos si hay filas sin resultado
        self.assertGreaterEqual(stats.csv_unique_patients, stats.csv_patients_with_orders)
        self.assertEqual(stats.csv_patients_without_orders, stats.csv_unique_patients - stats.csv_patients_with_orders)
        public = stats_as_public_dict(stats)
        self.assertNotIn("dni", public)
        self.assertTrue(all(isinstance(v, int) for v in public.values()))


class LabwinReconcileDbTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tm = TipoMuestra.objects.create(codigo="SUERO_RW", nombre="Suero", activo=True)
        for codigo in ("GLU", "UREA", "CREATI", "LEUCO", "HGB", "HTO", "HEMATIES"):
            TipoExamen.objects.create(
                codigo=codigo,
                nombre=codigo,
                tipo_muestra_requerida=tm,
                tipo_resultado="NUMERICO",
                precio=1,
                activo=True,
            )
        pac = Paciente.objects.create(dni="27831894", nombre="A", apellido="B")
        sol = SolicitudExamen(
            numero="LW-2022-00001",
            paciente=pac,
            origen_solicitud="EXTERNO_ICPL",
            estado="PENDIENTE",
            observaciones="Importado LabWin 1(1)",
        )
        # bypass save numbering
        SolicitudExamen.objects.bulk_create([sol])
        sol = SolicitudExamen.objects.get(numero="LW-2022-00001")
        from datetime import datetime
        from django.utils import timezone

        SolicitudExamen.objects.filter(pk=sol.pk).update(
            estado="FINALIZADO",
            fecha_solicitud=timezone.make_aware(datetime(2022, 6, 30, 12, 0)),
        )
        glu = TipoExamen.objects.get(codigo="GLU")
        urea = TipoExamen.objects.get(codigo="UREA")
        creati = TipoExamen.objects.get(codigo="CREATI")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=glu, valor_obtenido="75")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=urea, valor_obtenido="2.5")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=creati, valor_obtenido="0.6")

    def test_reconcile_identical_and_missing(self):
        stats = reconcile_orders_against_db(FIXTURE)
        self.assertGreaterEqual(stats.order_identical, 1)
        self.assertGreaterEqual(stats.order_missing_in_db, 1)
        self.assertEqual(stats.order_patient_mismatch, 0)
        self.assertEqual(stats.order_result_diff, 0)

    def test_command_readonly_output(self):
        from io import StringIO

        out = StringIO()
        call_command("reconcile_labwin_csv", str(FIXTURE), stdout=out)
        text = out.getvalue()
        self.assertIn("SOLO LECTURA", text)
        self.assertIn("order_identical=", text)
        self.assertNotIn("27831894", text)
