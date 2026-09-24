"""Corte A: equipos B12/VITD/PROBNP, MXD≠MONO, mapeo sin reescribir resultados."""
from __future__ import annotations

import uuid
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from laboratorio.equipos_lab import EXAMEN_A_EQUIPO, EXAMENES_FINECARE, EXAMENES_VIDAS
from laboratorio.instrumentos_catalogo import CODIGOS_SYSMEX_MXD, MAPEO_SYSMEX_XP300
from laboratorio.instrumentos_seed import asegurar_interfaz, desactivar_mapeos_mxd_a_mono
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_instrumentos import MapeoAnalitoInstrumento
from laboratorio.models_qc import EquipoAnalizador
from laboratorio.qc_service import estado_iqc_solicitud
from laboratorio.tests.test_qc_gate import _FakeSolicitud
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestEquiposCorteA(TestCase):
    def test_b12_vitd_vidas_probnp_finecare(self):
        self.assertIn("B12", EXAMENES_VIDAS)
        self.assertIn("VITD", EXAMENES_VIDAS)
        self.assertEqual(EXAMEN_A_EQUIPO["B12"], "VIDAS_KUBE")
        self.assertEqual(EXAMEN_A_EQUIPO["VITD"], "VIDAS_KUBE")
        self.assertIn("PROBNP", EXAMENES_FINECARE)
        self.assertEqual(EXAMEN_A_EQUIPO["PROBNP"], "FINECARE")


class TestSysmexMxdNoMono(TestCase):
    def test_catalogo_no_mapea_mxd_a_mono(self):
        for codigo in CODIGOS_SYSMEX_MXD:
            self.assertNotIn(codigo, MAPEO_SYSMEX_XP300)

    def test_desactiva_mapeo_legado_sin_tocar_resultados(self):
        suf = uuid.uuid4().hex[:6]
        tm = TipoMuestra.objects.create(codigo=f"SG{suf}", nombre="Sangre", activo=True)
        EquipoAnalizador.objects.create(codigo="SYSMEX_XP300", nombre="XP-300", activo=True)
        mono = TipoExamen.objects.create(
            codigo="MONO",
            nombre="Monocitos",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            activo=True,
            precio=1,
        )
        interfaz = asegurar_interfaz("SYSMEX_XP300")
        mapeo = MapeoAnalitoInstrumento.objects.create(
            interfaz=interfaz,
            codigo_instrumento="MXD",
            tipo_examen=mono,
            activo=True,
        )
        n = desactivar_mapeos_mxd_a_mono(interfaz)
        self.assertEqual(n, 1)
        mapeo.refresh_from_db()
        self.assertFalse(mapeo.activo)


class TestMapearEquiposNoTocaResultados(TestCase):
    def test_mapear_solo_actualiza_fk_equipo(self):
        suf = uuid.uuid4().hex[:6]
        tm = TipoMuestra.objects.create(codigo=f"SG{suf}", nombre="Sangre", activo=True)
        vidas = EquipoAnalizador.objects.create(
            codigo="VIDAS_KUBE", nombre="VIDAS", activo=True
        )
        EquipoAnalizador.objects.create(codigo="CM260", nombre="CM260", activo=True)
        b12 = TipoExamen.objects.create(
            codigo="B12",
            nombre="Vitamina B12",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            equipo_analizador=None,
            activo=True,
            precio=1,
        )
        pac = Paciente.objects.create(dni=f"D{suf}", nombre="A", apellido="B")
        esp = Especialidad.objects.create(nombre=f"E{suf}")
        med_u = User.objects.create_user(
            username=f"m{suf}", email=f"m{suf}@t.com", password="x", rol="medico"
        )
        med = Medico.objects.create(
            nombre="Dr", apellido="X", matricula=f"M{suf}", especialidad=esp, user=med_u
        )
        sol = SolicitudExamen.objects.create(
            paciente=pac, medico_interno=med, estado="PENDIENTE"
        )
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=b12,
            valor_obtenido="999",
            valor_numerico=Decimal("999"),
        )
        call_command("mapear_examenes_equipo", stdout=StringIO())
        b12.refresh_from_db()
        res.refresh_from_db()
        self.assertEqual(b12.equipo_analizador_id, vidas.id)
        self.assertEqual(res.valor_obtenido, "999")
        self.assertEqual(res.valor_numerico, Decimal("999"))


class TestIqcSinConfiguracion(TestCase):
    def test_sin_materiales_no_parece_ok_configurado(self):
        suf = uuid.uuid4().hex[:6]
        tm = TipoMuestra.objects.create(codigo=f"SG{suf}", nombre="Sangre", activo=True)
        eq = EquipoAnalizador.objects.create(codigo="CM260", nombre="CM260", activo=True)
        te = TipoExamen.objects.create(
            codigo=f"X{suf}"[:12],
            nombre="Examen sin QC",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            equipo_analizador=eq,
            activo=True,
            precio=1,
        )
        st = estado_iqc_solicitud(_FakeSolicitud([te.id]))
        self.assertTrue(st["ok"])
        self.assertFalse(st["aplicable"])
        self.assertTrue(st.get("sin_configuracion"))
        self.assertEqual(st.get("motivo_no_aplicable"), "sin_materiales_ni_productos")
