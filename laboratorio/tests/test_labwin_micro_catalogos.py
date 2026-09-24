"""
Tests del importador de catálogos microbiológicos LabWin.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import TestCase

from laboratorio.labwin_micro_catalog_corrections import (
    corregir_antibiotico,
    corregir_frase,
    corregir_microorganismo,
    filas_reporte_revision_conocidas,
)
from laboratorio.labwin_micro_csv import cell_str, iter_labwin_csv_rows, read_labwin_csv
from laboratorio.models_microbiologia import (
    Antibiotico,
    FraseRapidaAsociacionAnalisis,
    FraseRapidaMicrobiologia,
    Microorganismo,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "labwin_micro_catalog_minimo"


class TestLabwinMicroCorrections(TestCase):
    def test_as_ts_orto(self):
        as_ = corregir_antibiotico("AS", "AMPINICILINA-SULBACTAMA")
        self.assertEqual(as_.nombre_mostrar, "Ampicilina/sulbactam")
        self.assertEqual(as_.correccion_estado, "ORTOGRAFIA_AUTO")
        ts = corregir_antibiotico("TS", "TRIMETOP.+SULFAMETOXAZOL")
        self.assertEqual(ts.nombre_mostrar, "Trimetoprima/sulfametoxazol")

    def test_ttt_inactivo(self):
        r = corregir_antibiotico("TTT", "Esto es de prueba")
        self.assertFalse(r.activo)

    def test_ni_ta_pendiente(self):
        for code in ("NI", "TA"):
            r = corregir_antibiotico(code, "x")
            self.assertTrue(r.requiere_revision)
            self.assertEqual(r.correccion_estado, "PENDIENTE_REVISION")

    def test_entc_corrige_frase_sin_cruzar_catalogos(self):
        # ENTC pertenece a NEMOTEC; no propagar reglas a BACTE por código.
        r = corregir_frase("ENTC", "Enteroccocus faecalis.")
        self.assertEqual(r.nombre_mostrar, "Enterococcus faecalis")
        m = corregir_microorganismo("ENTC", "Enteroccocus faecalis")
        self.assertEqual(m.nombre_mostrar, "Enteroccocus faecalis")
        self.assertEqual(m.correccion_estado, "NINGUNA")

    def test_frase_umbral_y_fenotipo(self):
        gr = corregir_frase("gr1", "texto umbral")
        self.assertEqual(gr.categoria, "UMBRAL")
        self.assertTrue(gr.requiere_revision)
        cont = corregir_frase("CONT", "contaminacion")
        self.assertEqual(cont.categoria, "FENOTIPO")

    def test_filas_reporte_keys(self):
        rows = filas_reporte_revision_conocidas()
        self.assertTrue(rows)
        for row in rows:
            self.assertIn("origen", row)
            self.assertIn("codigo", row)
            self.assertIn("original", row)
            self.assertIn("propuesta", row)
            self.assertIn("motivo", row)


class TestLabwinMicroCsv(TestCase):
    def test_null_vs_empty_string(self):
        path = FIXTURES / "_tmp_null.csv"
        # header + row with trailing unquoted NULL and a quoted empty
        path.write_text(
            '"A","B","C"\n'
            '"x",,"",\n',
            encoding="utf-8",
        )
        try:
            rows = read_labwin_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["A"], "x")
            self.assertIsNone(rows[0]["B"])
            self.assertEqual(rows[0]["C"], "")
            # trailing empty after last comma may be None
            self.assertEqual(cell_str(None), "")
        finally:
            path.unlink(missing_ok=True)

    def test_fixtures_multiline_nemotec(self):
        rows = list(iter_labwin_csv_rows(FIXTURES / "NEMOTEC.csv"))
        by_abrev = {r["ABREV_FLD"]: r for r in rows}
        self.assertIn("gr1", by_abrev)
        self.assertIn("\n", by_abrev["gr1"]["TEXTO_FLD"] or "")


@pytest.mark.django_db
class TestImportLabwinMicroCatalogos(TestCase):
    def test_dry_run_fixtures(self):
        call_command("import_labwin_micro_catalogos", fixtures=True, dry_run=True)
        self.assertEqual(Antibiotico.objects.filter(origen="LABWIN_ANTIB").count(), 0)
        self.assertEqual(Microorganismo.objects.filter(origen="LABWIN_BACTE").count(), 0)

    def test_import_idempotent_and_corrections(self):
        call_command("import_labwin_micro_catalogos", fixtures=True)
        as_ = Antibiotico.objects.get(codigo="AS")
        self.assertEqual(as_.nombre, "Ampicilina/sulbactam")
        self.assertEqual(as_.nombre_original, "AMPINICILINA-SULBACTAMA")
        self.assertFalse(Antibiotico.objects.get(codigo="TTT").activo)
        self.assertTrue(Antibiotico.objects.get(codigo="NI").requiere_revision)

        n1 = Antibiotico.objects.filter(origen="LABWIN_ANTIB").count()
        m1 = Microorganismo.objects.filter(origen="LABWIN_BACTE").count()
        f1 = FraseRapidaMicrobiologia.objects.filter(origen="LABWIN_NEMOTEC").count()
        a1 = FraseRapidaAsociacionAnalisis.objects.count()
        self.assertGreater(n1, 0)
        self.assertGreater(m1, 0)
        self.assertGreater(f1, 0)
        self.assertGreater(a1, 0)

        call_command("import_labwin_micro_catalogos", fixtures=True)
        self.assertEqual(Antibiotico.objects.filter(origen="LABWIN_ANTIB").count(), n1)
        self.assertEqual(Microorganismo.objects.filter(origen="LABWIN_BACTE").count(), m1)
        self.assertEqual(FraseRapidaMicrobiologia.objects.filter(origen="LABWIN_NEMOTEC").count(), f1)

    def test_editado_manualmente_preserva_nombre(self):
        call_command("import_labwin_micro_catalogos", fixtures=True)
        ab = Antibiotico.objects.get(codigo="AS")
        ab.nombre = "Nombre manual"
        ab.editado_manualmente = True
        ab.save()
        call_command("import_labwin_micro_catalogos", fixtures=True)
        ab.refresh_from_db()
        self.assertEqual(ab.nombre, "Nombre manual")

    def test_psa_namespaces_separados(self):
        call_command("import_labwin_micro_catalogos", fixtures=True)
        self.assertTrue(Microorganismo.objects.filter(codigo="PSA").exists())
        self.assertTrue(FraseRapidaMicrobiologia.objects.filter(abreviatura="PSA").exists())


@pytest.mark.django_db
class TestFrasePermisosYHalo(TestCase):
    def test_permisos_y_resultado_con_halo(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        from laboratorio.models_microbiologia import (
            AisladoMicrobiologico,
            Antibiograma,
            EstudioMicrobiologia,
            LecturaCultivo,
            MedioCultivo,
            ResultadoAntibiotico,
            SiembraMicrobiologia,
            TipoCultivoMicrobiologia,
            TipoMuestraMicrobiologia,
        )
        from pacientes.models import Paciente

        User = get_user_model()
        lab = User.objects.create_user(username="lab_lw", password="x", rol="laboratorio")
        med = User.objects.create_user(username="med_lw", password="x", rol="medico")
        client = APIClient()
        client.force_authenticate(user=lab)
        r = client.post(
            "/api/lab/microbiologia/frases-rapidas/",
            {"abreviatura": "TX1", "texto": "Texto", "categoria": "GENERAL"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        client.force_authenticate(user=med)
        r2 = client.post(
            "/api/lab/microbiologia/frases-rapidas/",
            {"abreviatura": "TX2", "texto": "No", "categoria": "GENERAL"},
            format="json",
        )
        self.assertIn(r2.status_code, (401, 403))

        pac = Paciente.objects.create(nombre="T", apellido="E", dni="99887766")
        tc = TipoCultivoMicrobiologia.objects.create(codigo="URO_LW", nombre="Uro")
        tm = TipoMuestraMicrobiologia.objects.create(codigo="ORI_LW", nombre="Orina")
        est = EstudioMicrobiologia.objects.create(
            paciente=pac, tipo_cultivo=tc, tipo_muestra_micro=tm, estado="IDENTIFICACION"
        )
        medio = MedioCultivo.objects.create(codigo="AS_LW", nombre="AS")
        siembra = SiembraMicrobiologia.objects.create(estudio=est, medio=medio, estado="SEMBRADA")
        lectura = LecturaCultivo.objects.create(estudio=est, siembra=siembra, crecimiento="MODERADO")
        micro = Microorganismo.objects.create(codigo="ECO_LW", nombre="E. coli", activo=True)
        aislado = AisladoMicrobiologico.objects.create(
            estudio=est, lectura_origen=lectura, microorganismo=micro, estado="IDENTIFICADO"
        )
        ab = Antibiotico.objects.create(codigo="AM_LW", nombre="Ampicilina", activo=True)
        antib = Antibiograma.objects.create(aislado=aislado, estado="PENDIENTE")
        client.force_authenticate(user=lab)
        r3 = client.post(
            "/api/lab/microbiologia/resultados-antibiotico/",
            {
                "antibiograma_id": antib.pk,
                "antibiotico_id": ab.pk,
                "interpretacion": "S",
                "halo_mm": "18.00",
                "metodo": "Kirby-Bauer",
                "estandar_version": "CLSI M100 2024",
            },
            format="json",
        )
        self.assertEqual(r3.status_code, 201, r3.data)
        res = ResultadoAntibiotico.objects.get(pk=r3.data["id"])
        self.assertEqual(str(res.halo_mm), "18.00")
        self.assertEqual(res.interpretacion, "S")
        self.assertEqual(res.metodo, "Kirby-Bauer")
