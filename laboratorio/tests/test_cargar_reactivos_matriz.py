"""Dry-run y --apply catálogo reactivos Ticket B."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from laboratorio.models_inventario import ConsumoInsumoExamen, InsumoLab, MovimientoStock
from laboratorio.models_qc import EquipoAnalizador
from laboratorio.reactivos_matriz_catalogo import (
    REACTIVOS_CATALOGO_CONFIRMADOS,
    REACTIVOS_CATALOGO_PENDIENTES,
)


class _BaseEquiposMixin:
    def _seed_equipos_y_legacy(self):
        EquipoAnalizador.objects.create(codigo="CM260", nombre="CM260", activo=True)
        EquipoAnalizador.objects.create(codigo="VIDAS_KUBE", nombre="VIDAS", activo=True)
        EquipoAnalizador.objects.create(codigo="FINECARE", nombre="Finecare", activo=True)
        InsumoLab.objects.create(
            codigo="CRE",
            nombre="CREATININA COLORIMETRICA",
            tipo=InsumoLab.Tipo.REACTIVO,
            proveedor="PHARMACORP",
            equipo=EquipoAnalizador.objects.get(codigo="CM260"),
            activo=True,
        )
        InsumoLab.objects.create(
            codigo="GLU",
            nombre="GLICEMIA ENZIMATICA AA",
            tipo=InsumoLab.Tipo.REACTIVO,
            proveedor="PHARMACORP",
            equipo=EquipoAnalizador.objects.get(codigo="CM260"),
            activo=True,
        )


class TestCargarReactivosDryRun(_BaseEquiposMixin, TestCase):
    def setUp(self):
        self._seed_equipos_y_legacy()

    def test_dry_run_no_escribe(self):
        before_insumos = InsumoLab.objects.count()
        before_mov = MovimientoStock.objects.count()
        before_cons = ConsumoInsumoExamen.objects.count()
        out = StringIO()
        call_command("cargar_reactivos_equipo_matriz", stdout=out)
        text = out.getvalue()
        self.assertIn("Dry-run", text)
        self.assertIn("R-1008149", text)
        self.assertIn("R-W216", text)
        self.assertIn("PROT_U_AZ,PROT_U_24", text.replace(" ", ""))
        self.assertIn("CPK_MB,MIOG,TROP_I", text.replace(" ", ""))
        self.assertEqual(InsumoLab.objects.count(), before_insumos)
        self.assertEqual(MovimientoStock.objects.count(), before_mov)
        self.assertEqual(ConsumoInsumoExamen.objects.count(), before_cons)
        cre = InsumoLab.objects.get(codigo="CRE")
        self.assertEqual(cre.proveedor, "PHARMACORP")
        self.assertEqual(cre.ref_comercial, "")
        glu = InsumoLab.objects.get(codigo="GLU")
        self.assertEqual(glu.proveedor, "PHARMACORP")

    def test_matriz_tiene_confirmados_sin_ferr(self):
        refs = {r["ref_comercial"] for r in REACTIVOS_CATALOGO_CONFIRMADOS}
        self.assertIn("W216", refs)
        self.assertIn("1008161", refs)
        self.assertNotIn("", refs)
        codigos = {r["codigo"] for r in REACTIVOS_CATALOGO_CONFIRMADOS}
        self.assertNotIn("CRE", codigos)
        self.assertNotIn("GLU", codigos)
        self.assertTrue(any(p["lis"] == "FERR" for p in REACTIVOS_CATALOGO_PENDIENTES))


class TestCargarReactivosApply(_BaseEquiposMixin, TestCase):
    def setUp(self):
        self._seed_equipos_y_legacy()

    def test_apply_crea_22_sin_stock_ni_consumos(self):
        before_mov = MovimientoStock.objects.count()
        before_cons = ConsumoInsumoExamen.objects.count()
        out = StringIO()
        call_command("cargar_reactivos_equipo_matriz", "--apply", stdout=out)
        self.assertIn("APPLY OK", out.getvalue())
        expected = {r["codigo"] for r in REACTIVOS_CATALOGO_CONFIRMADOS}
        creados = InsumoLab.objects.filter(codigo__in=expected)
        self.assertEqual(creados.count(), 22)
        for ins in creados:
            self.assertEqual(ins.tipo, InsumoLab.Tipo.REACTIVO)
            self.assertTrue((ins.ref_comercial or "").strip())
            self.assertEqual(ins.stock_actual, 0)
            self.assertIsNotNone(ins.equipo_id)
        self.assertFalse(
            InsumoLab.objects.filter(codigo__icontains="FERR").exists()
        )
        self.assertEqual(MovimientoStock.objects.count(), before_mov)
        self.assertEqual(ConsumoInsumoExamen.objects.count(), before_cons)
        cre = InsumoLab.objects.get(codigo="CRE")
        glu = InsumoLab.objects.get(codigo="GLU")
        self.assertEqual(cre.proveedor, "PHARMACORP")
        self.assertEqual(glu.proveedor, "PHARMACORP")
        self.assertEqual(cre.ref_comercial, "")
        self.assertEqual(glu.ref_comercial, "")

    def test_apply_idempotente(self):
        call_command("cargar_reactivos_equipo_matriz", "--apply", stdout=StringIO())
        n1 = InsumoLab.objects.filter(tipo=InsumoLab.Tipo.REACTIVO).count()
        mov1 = MovimientoStock.objects.count()
        cons1 = ConsumoInsumoExamen.objects.count()
        out = StringIO()
        call_command("cargar_reactivos_equipo_matriz", "--apply", stdout=out)
        text = out.getvalue()
        self.assertIn("Nuevos: 0", text)
        self.assertEqual(
            InsumoLab.objects.filter(tipo=InsumoLab.Tipo.REACTIVO).count(), n1
        )
        self.assertEqual(MovimientoStock.objects.count(), mov1)
        self.assertEqual(ConsumoInsumoExamen.objects.count(), cons1)

    def test_conflicto_ref_equipo_no_crea_sku_ambiguo(self):
        eq = EquipoAnalizador.objects.get(codigo="CM260")
        InsumoLab.objects.create(
            codigo="OTRO-1008149",
            nombre="Ambiguo",
            tipo=InsumoLab.Tipo.REACTIVO,
            ref_comercial="1008149",
            equipo=eq,
            activo=True,
        )
        call_command("cargar_reactivos_equipo_matriz", "--apply", stdout=StringIO())
        self.assertFalse(InsumoLab.objects.filter(codigo="R-1008149").exists())
        self.assertTrue(InsumoLab.objects.filter(codigo="R-1008156").exists())
