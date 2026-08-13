from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from laboratorio.labwin_csv import (
    COLUMNA_A_CODIGO,
    extraer_eab_layout_b,
    format_protocolo_labwin,
    inferir_tipo_eab,
    is_empty,
    load_labwin_csv,
    parse_valor_numerico,
    uniquify_headers,
)
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente

FIXTURE = Path(__file__).parent / "fixtures" / "labwin_min.csv"


class LabwinParserTests(SimpleTestCase):
    def test_empty_markers(self):
        self.assertTrue(is_empty("------------"))
        self.assertTrue(is_empty("-11"))
        self.assertTrue(is_empty(""))
        self.assertFalse(is_empty("0"))
        self.assertFalse(is_empty("14.1"))

    def test_protocolo(self):
        self.assertEqual(format_protocolo_labwin(date(2022, 6, 30), "1(1)"), "LW-2022-00001")
        self.assertEqual(format_protocolo_labwin(date(2026, 8, 12), "28303(27776)"), "LW-2026-28303")

    def test_uniquify_na(self):
        headers = uniquify_headers(["Na", "K", "Cl", "Na", "K", "Cl"])
        self.assertEqual(headers, ["Na", "K", "Cl", "Na#2", "K#2", "Cl#2"])
        self.assertIn("Na", COLUMNA_A_CODIGO)
        self.assertNotIn("Na#2", COLUMNA_A_CODIGO)

    def test_parse_numerico(self):
        self.assertEqual(parse_valor_numerico("14.1"), Decimal("14.1"))
        self.assertEqual(parse_valor_numerico("<150"), Decimal("150"))
        self.assertEqual(parse_valor_numerico(">2.500,0"), Decimal("2500.0"))
        self.assertIsNone(parse_valor_numerico("No contiene"))
        self.assertEqual(parse_valor_numerico("+10.6"), Decimal("10.6"))
        self.assertEqual(parse_valor_numerico("-0,2"), Decimal("-0.2"))

    def test_eab_layout_b_art_y_ven(self):
        art = extraer_eab_layout_b(
            {"pH": "7.39", "Ox": "100", "pCO2": "46.7", "Sat": "100", "Bic": "26.5", "Eb": "0.2"}
        )
        self.assertIsNotNone(art)
        res, panel = art
        self.assertEqual(panel, "PAN_EAB_ART")
        self.assertEqual(res["PH_ART"], "7.39")
        self.assertEqual(res["PO2_ART"], "100")
        ven = extraer_eab_layout_b(
            {"pH": "7.34", "Ox": "40", "pCO2": "40.7", "Sat": "75", "Bic": "25", "Eb": "1.3"}
        )
        self.assertIsNotNone(ven)
        self.assertEqual(ven[1], "PAN_EAB_VEN")
        self.assertIn("PH_VEN", ven[0])

    def test_eab_be_menos_11_y_sin_be(self):
        con_be = extraer_eab_layout_b(
            {"pH": "7.4", "Ox": "82", "pCO2": "22.2", "Sat": "96", "Bic": "13.4", "Eb": "-11"}
        )
        self.assertIsNotNone(con_be)
        self.assertEqual(con_be[1], "PAN_EAB_ART")
        self.assertEqual(con_be[0]["BE_ART"], "-11")
        doble = extraer_eab_layout_b(
            {"pH": "7.38", "Ox": "69", "pCO2": "22.9", "Sat": "94", "Bic": "13.2", "Eb": "--11.9"}
        )
        self.assertIsNotNone(doble)
        self.assertEqual(doble[0]["BE_VEN"], "-11.9")
        sin_be = extraer_eab_layout_b(
            {"pH": "7.23", "Ox": "41", "pCO2": "34.4", "Sat": "68", "Bic": "14.4", "Eb": "__________"}
        )
        self.assertIsNotNone(sin_be)
        self.assertEqual(sin_be[1], "PAN_EAB_VEN")
        self.assertNotIn("BE_VEN", sin_be[0])
        self.assertEqual(sin_be[0]["PH_VEN"], "7.23")

    def test_eab_layout_viejo_se_omite(self):
        self.assertIsNone(
            extraer_eab_layout_b(
                {"pH": "7.44", "Ox": "27", "pCO2": "0.3", "Sat": "41.7", "Bic": "64.5", "Eb": "904"}
            )
        )

    def test_inferir_tipo_eab(self):
        self.assertEqual(inferir_tipo_eab(Decimal("100"), Decimal("91")), "ART")
        self.assertEqual(inferir_tipo_eab(Decimal("55"), Decimal("96")), "ART")
        self.assertEqual(inferir_tipo_eab(Decimal("40"), Decimal("75")), "VEN")

    def test_load_fixture(self):
        patients, orders, stats = load_labwin_csv(FIXTURE)
        self.assertEqual(stats.unique_patients, 2)
        self.assertEqual(len(orders), 4)
        self.assertEqual(stats.eab_art, 1)
        self.assertEqual(stats.eab_ven, 1)
        self.assertEqual(stats.eab_omitido_layout_viejo, 1)
        glu_order = next(o for o in orders if o.protocolo == "LW-2022-00001")
        self.assertNotIn("PH_ART", glu_order.resultados)
        self.assertNotIn("PH_VEN", glu_order.resultados)
        art = next(o for o in orders if o.protocolo == "LW-2025-00020")
        self.assertEqual(art.resultados["SAT_O2_ART"], "100")
        self.assertEqual(art.paneles, ["PAN_EAB_ART"])
        ven = next(o for o in orders if o.protocolo == "LW-2025-00021")
        self.assertEqual(ven.resultados["PO2_VEN"], "40")
        self.assertEqual(stats.dni_omitidos_revision, 1)
        self.assertIn("27831894", patients)
        self.assertNotIn("10378931", patients)
        self.assertEqual(patients["27831894"].apellido, "FUENTEALBA")
        self.assertEqual(patients["27831894"].telefono, "12345678901234567890")
        self.assertEqual(len(patients["27831894"].telefono), 20)
        self.assertEqual(patients["22798582"].telefono, "1111111111")
        glu_order = next(o for o in orders if o.protocolo == "LW-2022-00001")
        self.assertEqual(glu_order.resultados["GLU"], "75")
        self.assertEqual(glu_order.resultados["UREA"], "2.5")
        hemo = next(o for o in orders if o.protocolo == "LW-2022-00010")
        self.assertEqual(hemo.resultados["LEUCO"], "81")
        self.assertEqual(hemo.dni, "22798582")


class LabwinImportCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tm = TipoMuestra.objects.create(codigo="SUERO_LW", nombre="Suero", activo=True)
        for codigo, nombre in (
            ("CREATI", "Creatininemia"),
            ("GLU", "Glucemia"),
            ("UREA", "Uremia"),
            ("LEUCO", "Leucocitos"),
            ("HGB", "Hemoglobina"),
            ("HTO", "Hematocrito"),
            ("HEMATIES", "Hematíes"),
            ("PH_ART", "pH arterial"),
            ("PO2_ART", "pO2 arterial"),
            ("PCO2_ART", "pCO2 arterial"),
            ("SAT_O2_ART", "Sat O2 arterial"),
            ("HCO3_ART", "HCO3 arterial"),
            ("BE_ART", "BE arterial"),
            ("PH_VEN", "pH venoso"),
            ("PO2_VEN", "pO2 venoso"),
            ("PCO2_VEN", "pCO2 venoso"),
            ("SAT_O2_VEN", "Sat O2 venoso"),
            ("HCO3_VEN", "HCO3 venoso"),
            ("BE_VEN", "BE venoso"),
        ):
            TipoExamen.objects.create(
                codigo=codigo,
                nombre=nombre,
                tipo_muestra_requerida=tm,
                tipo_resultado="NUMERICO",
                precio=1,
                activo=True,
            )
        pan_art = PanelExamen.objects.create(codigo="PAN_EAB_ART", nombre="EAB arterial", activo=True)
        pan_ven = PanelExamen.objects.create(codigo="PAN_EAB_VEN", nombre="EAB venoso", activo=True)
        pan_art.tipos_examen.add(*TipoExamen.objects.filter(codigo__endswith="_ART"))
        pan_ven.tipos_examen.add(*TipoExamen.objects.filter(codigo__endswith="_VEN"))
        Paciente.objects.create(
            dni="22798582",
            nombre="Fernando Javier",
            apellido="Piccone Rey",
            telefono="999",
        )

    def test_dry_run_no_write(self):
        before = Paciente.objects.count()
        call_command("import_labwin_csv", str(FIXTURE), dry_run=True, verbosity=0)
        self.assertEqual(Paciente.objects.count(), before)
        self.assertEqual(SolicitudExamen.objects.count(), 0)

    def test_import_creates_patient_and_orders_idempotent(self):
        call_command("import_labwin_csv", str(FIXTURE), verbosity=0)
        self.assertTrue(Paciente.objects.filter(dni="27831894").exists())
        existente = Paciente.objects.get(dni="22798582")
        self.assertEqual(existente.telefono, "999")
        self.assertEqual(SolicitudExamen.objects.count(), 4)
        sol = SolicitudExamen.objects.get(numero="LW-2022-00001")
        self.assertEqual(sol.estado, "FINALIZADO")
        self.assertEqual(sol.origen_solicitud, "EXTERNO_ICPL")
        self.assertEqual(sol.fecha_solicitud.date().isoformat(), "2022-06-30")
        glu = ResultadoExamen.objects.get(solicitud=sol, tipo_examen__codigo="GLU")
        self.assertEqual(glu.valor_obtenido, "75")
        self.assertFalse(
            ResultadoExamen.objects.filter(solicitud=sol, tipo_examen__codigo="PH_ART").exists()
        )
        art = SolicitudExamen.objects.get(numero="LW-2025-00020")
        self.assertTrue(art.paneles.filter(codigo="PAN_EAB_ART").exists())
        self.assertEqual(
            ResultadoExamen.objects.get(solicitud=art, tipo_examen__codigo="SAT_O2_ART").valor_obtenido,
            "100",
        )
        ven = SolicitudExamen.objects.get(numero="LW-2025-00021")
        self.assertTrue(ven.paneles.filter(codigo="PAN_EAB_VEN").exists())

        n_res = ResultadoExamen.objects.count()
        call_command("import_labwin_csv", str(FIXTURE), verbosity=0)
        self.assertEqual(SolicitudExamen.objects.count(), 4)
        self.assertEqual(ResultadoExamen.objects.count(), n_res)
        self.assertEqual(Paciente.objects.filter(dni="27831894").count(), 1)

    def test_eab_completa_orden_existente(self):
        call_command("import_labwin_csv", str(FIXTURE), verbosity=0)
        art = SolicitudExamen.objects.get(numero="LW-2025-00020")
        ResultadoExamen.objects.filter(
            solicitud=art, tipo_examen__codigo__endswith="_ART"
        ).delete()
        art.paneles.clear()
        call_command("import_labwin_csv", str(FIXTURE), verbosity=0)
        self.assertTrue(
            ResultadoExamen.objects.filter(
                solicitud=art, tipo_examen__codigo="PH_ART"
            ).exists()
        )
        art.refresh_from_db()
        self.assertTrue(art.paneles.filter(codigo="PAN_EAB_ART").exists())
