"""Interfaz analizadores: worklist, ingesta, ASTM, compact ID."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.instrumentos_astm import (
    decode_frame,
    encode_frame,
    parse_resultados,
    sample_id_from_query,
    split_records,
)
from laboratorio.instrumentos_seed import asegurar_interfaz, seed_mapeos_interfaz
from laboratorio.instrumentos_service import IngestaItem, consulta_trabajo, ingestar_resultados
from laboratorio.lab_codigo import codigo_instrumento_desde_tubo
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_instrumentos import MensajeInstrumento
from laboratorio.models_qc import EquipoAnalizador, ProductoControl
from laboratorio.muestra_estado import aplicar_recibir, crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestAstmCodec(TestCase):
    def test_frame_roundtrip_y_checksum(self):
        raw = encode_frame("H|\\^&|", 1, last=True)
        self.assertTrue(raw.startswith(b"\x02"))
        self.assertEqual(decode_frame(raw), "H|\\^&|")

    def test_query_sample_id(self):
        recs = split_records("H|\\^&\rQ|1|^20260004201\rL|1|N\r")
        self.assertEqual(sample_id_from_query(recs), "20260004201")

    def test_parse_resultados_sysmex(self):
        msg = "H|\\^&\rP|1\rO|1|20260004201\rR|1|^^^WBC|9.3|10*3/uL\rR|2|^^^HGB|13.1|g/dL\rL|1|N\r"
        sid, rows = parse_resultados(split_records(msg))
        self.assertEqual(sid, "20260004201")
        self.assertEqual(rows[0].codigo, "WBC")
        self.assertEqual(rows[0].valor, "9.3")
        self.assertEqual(rows[1].codigo, "HGB")


class TestInstrumentosIntegracion(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.lab = User.objects.create_user(
            username=f"lab_ins_{suf}",
            email=f"li{suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.medico_user = User.objects.create_user(
            username=f"med_ins_{suf}",
            email=f"mi{suf}@t.com",
            password="x",
            rol="medico",
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="X", matricula=f"M{suf}", especialidad=esp, user=self.medico_user
        )
        self.paciente = Paciente.objects.create(
            dni=f"D{suf}", nombre="Ana", apellido="Test"
        )
        self.tm = TipoMuestra.objects.create(codigo=f"SG{suf}", nombre="Sangre", activo=True)
        self.eq = EquipoAnalizador.objects.create(codigo="CM260", nombre="CM260", activo=True)
        self.eq_hemo = EquipoAnalizador.objects.create(
            codigo="SYSMEX_XP300", nombre="XP-300", activo=True
        )
        self.glu = TipoExamen.objects.create(
            codigo="GLU",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.eq,
            activo=True,
            precio=1,
        )
        self.urea = TipoExamen.objects.create(
            codigo="UREA",
            nombre="Urea",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.eq,
            activo=True,
            precio=1,
        )
        self.creati = TipoExamen.objects.create(
            codigo="CREATI",
            nombre="Creatinina",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.eq,
            activo=True,
            precio=1,
        )
        self.leuco = TipoExamen.objects.create(
            codigo="LEUCO",
            nombre="Leucocitos",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            equipo_analizador=self.eq_hemo,
            activo=True,
            precio=1,
        )
        self.if_cm = asegurar_interfaz("CM260")
        self.if_xp = asegurar_interfaz("SYSMEX_XP300")
        seed_mapeos_interfaz(self.if_cm)
        seed_mapeos_interfaz(self.if_xp)
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(user=self.lab)

    def _orden_con_tubo(self, *examenes, estado_orden="EN_PROCESO"):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado=estado_orden,
        )
        for ex in examenes:
            sol.tipos_examen.add(ex)
            ResultadoExamen.objects.get_or_create(solicitud=sol, tipo_examen=ex)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=self.lab,
            view="t",
        )
        aplicar_recibir(m.pk, actor=self.lab, view="t")
        m.refresh_from_db()
        return sol, m

    def test_compact_id(self):
        self.assertEqual(codigo_instrumento_desde_tubo("LAB-2026-00042-01"), "20260004201")

    def test_worklist_y_ingesta_cm260(self):
        sol, m = self._orden_con_tubo(self.glu, self.urea)
        wl = consulta_trabajo(sample_id=m.codigo_barra, interfaz=self.if_cm, actor=self.lab)
        self.assertEqual(wl.estado, MensajeInstrumento.Estado.OK)
        codes = {a.codigo_instrumento for a in wl.analitos}
        self.assertIn("GLU", codes)
        self.assertIn("URE", codes)
        ing = ingestar_resultados(
            sample_id=m.codigo_instrumento,
            interfaz=self.if_cm,
            items=[
                IngestaItem(codigo_instrumento="GLU", valor="98"),
                IngestaItem(codigo_instrumento="URE", valor="35"),
            ],
            actor=self.lab,
        )
        self.assertEqual(ing.estado, MensajeInstrumento.Estado.OK)
        self.assertEqual(ing.cargados, 2)
        sol.refresh_from_db()
        self.assertNotEqual(sol.estado, "FINALIZADO")
        glu = ResultadoExamen.objects.get(solicitud=sol, tipo_examen=self.glu)
        self.assertTrue((glu.valor_obtenido or "").strip())
        self.assertIsNone(glu.validado_por_id)

    def test_cre_mapea_a_creati(self):
        sol, m = self._orden_con_tubo(self.creati)
        ing = ingestar_resultados(
            sample_id=m.codigo_barra,
            interfaz=self.if_cm,
            items=[IngestaItem(codigo_instrumento="CRE", valor="0.9")],
            actor=self.lab,
        )
        self.assertEqual(ing.estado, MensajeInstrumento.Estado.OK)
        row = ResultadoExamen.objects.get(solicitud=sol, tipo_examen=self.creati)
        self.assertIn("0.9", row.valor_obtenido)

    def test_analito_desconocido_no_crea_fila(self):
        sol, m = self._orden_con_tubo(self.glu)
        n_antes = ResultadoExamen.objects.filter(solicitud=sol).count()
        ing = ingestar_resultados(
            sample_id=m.codigo_barra,
            interfaz=self.if_cm,
            items=[IngestaItem(codigo_instrumento="NOEXISTE", valor="1")],
            actor=self.lab,
        )
        self.assertEqual(ing.estado, MensajeInstrumento.Estado.SIN_MATCH)
        self.assertEqual(ResultadoExamen.objects.filter(solicitud=sol).count(), n_antes)
        glu = ResultadoExamen.objects.get(solicitud=sol, tipo_examen=self.glu)
        self.assertEqual((glu.valor_obtenido or "").strip(), "")

    def test_sysmex_compact_id_y_wbc(self):
        sol, m = self._orden_con_tubo(self.leuco)
        self.assertTrue(m.codigo_instrumento)
        wl = consulta_trabajo(sample_id=m.codigo_instrumento, interfaz=self.if_xp, actor=self.lab)
        self.assertEqual(wl.estado, MensajeInstrumento.Estado.OK)
        self.assertTrue(any(a.codigo_instrumento == "WBC" for a in wl.analitos))
        ing = ingestar_resultados(
            sample_id=m.codigo_instrumento,
            interfaz=self.if_xp,
            items=[IngestaItem(codigo_instrumento="WBC", valor="9.3")],
            actor=self.lab,
        )
        self.assertEqual(ing.estado, MensajeInstrumento.Estado.OK)
        row = ResultadoExamen.objects.get(solicitud=sol, tipo_examen=self.leuco)
        self.assertEqual(str(row.valor_numerico), "9.3000")

    def test_iqc_bloquea_worklist_e_ingesta(self):
        ProductoControl.objects.create(
            codigo="STANDATROL_SE",
            nombre="Standatrol",
            equipo=self.eq,
            modo=ProductoControl.Modo.MULTIPARAM,
            activo=True,
        )
        _sol, m = self._orden_con_tubo(self.glu)
        wl = consulta_trabajo(sample_id=m.codigo_barra, interfaz=self.if_cm, actor=self.lab)
        self.assertEqual(wl.estado, MensajeInstrumento.Estado.IQC_BLOQUEADO)
        self.assertEqual(wl.analitos, [])
        ing = ingestar_resultados(
            sample_id=m.codigo_barra,
            interfaz=self.if_cm,
            items=[IngestaItem(codigo_instrumento="GLU", valor="100")],
            actor=self.lab,
        )
        self.assertEqual(ing.estado, MensajeInstrumento.Estado.IQC_BLOQUEADO)
        glu = ResultadoExamen.objects.get(tipo_examen=self.glu, solicitud=_sol)
        self.assertEqual((glu.valor_obtenido or "").strip(), "")

    def test_api_consulta_e_ingesta(self):
        _sol, m = self._orden_con_tubo(self.glu)
        r = self.client.post(
            "/api/lab/instrumentos/consulta-trabajo/",
            {"interfaz_id": self.if_cm.id, "sample_id": m.codigo_barra},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["estado"], "OK")
        r2 = self.client.post(
            "/api/lab/instrumentos/ingesta/",
            {
                "interfaz_id": self.if_cm.id,
                "sample_id": m.codigo_barra,
                "resultados": [{"codigo_instrumento": "GLU", "valor": "101"}],
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data["cargados"], 1)

    @override_settings(LIMS_INSTRUMENT_TOKEN="secret-inst-token")
    def test_token_gateway(self):
        _sol, m = self._orden_con_tubo(self.glu)
        anon = APIClient(enforce_csrf_checks=False)
        r = anon.post(
            "/api/lab/instrumentos/consulta-trabajo/",
            {"interfaz_id": self.if_cm.id, "sample_id": m.codigo_barra},
            format="json",
            HTTP_X_LIMS_INSTRUMENT_TOKEN="secret-inst-token",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_medico_no_lista_interfaces(self):
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get("/api/lab/instrumentos/interfaces/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
