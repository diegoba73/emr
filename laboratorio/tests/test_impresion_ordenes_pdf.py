"""Impresión desde bandeja de órdenes: listado del día y pedidos formato papel."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.impresion_ordenes_pdf import (
    ImpresionOrdenesError,
    MICRO_CULTIVO_DE,
    construir_pedido_clinico,
    construir_pedido_micro,
    generar_pedidos_papel_pdf_bytes,
    parsear_items,
    parsear_resenas,
)
from laboratorio.resena_pedido import ContextoResena, construir_resena_reglas
from laboratorio.models import PanelExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_microbiologia import EstudioMicrobiologia, TipoCultivoMicrobiologia
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()

URL_LISTADO = "/api/lab/ordenes/listado-dia-pdf/"
URL_PEDIDOS = "/api/lab/ordenes/pedidos-papel-pdf/"
URL_RESENAS = "/api/lab/ordenes/resenas-sugeridas/"


def _paginas(pdf: bytes) -> int:
    return pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")


def _examen(codigo: str, nombre: str, tm: TipoMuestra) -> TipoExamen:
    te, _ = TipoExamen.objects.get_or_create(
        codigo=codigo,
        defaults={"nombre": nombre, "tipo_muestra_requerida": tm, "precio": 1, "activo": True},
    )
    return te


def _cultivo(codigo: str, nombre: str) -> TipoCultivoMicrobiologia:
    tc, _ = TipoCultivoMicrobiologia.objects.get_or_create(
        codigo=codigo, defaults={"nombre": nombre, "activo": True}
    )
    return tc


class TestImpresionOrdenes(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_imp_{suf}", email=f"lab-imp-{suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_imp_{suf}", email=f"med-imp-{suf}@t.com",
            password="x", rol="medico", is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"6{suf[:7]}", nombre="Juan", apellido="Pérez",
            obra_social="OSDE", numero_afiliado="123/45",
        )
        self.paciente2 = Paciente.objects.create(
            dni=f"5{suf[:7]}", nombre="Ana", apellido="López",
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.medico = Medico.objects.create(
            nombre="Ana", apellido="García", matricula=f"M-{suf}", especialidad=esp
        )
        tm = TipoMuestra.objects.create(codigo=f"TM{suf}", nombre="Sangre", activo=True)
        self.glu = _examen("GLU", "Glucemia", tm)
        self.hgb = _examen("HGB", "Hemoglobina", tm)
        self.extra = _examen(f"X{suf}", "Examen fuera de formulario", tm)
        self.hemo, _ = PanelExamen.objects.get_or_create(
            codigo="PAN_HEMO", defaults={"nombre": "Hemograma", "activo": True}
        )
        self.hemo.tipos_examen.add(self.hgb)

        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente, medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO",
        )
        self.sol.paneles.add(self.hemo)
        self.sol.tipos_examen.add(self.glu, self.hgb, self.extra)

        uro = _cultivo("UROCULTIVO", "Urocultivo")
        hemo_c = _cultivo("HEMOCULTIVO", "Hemocultivo")
        uretral = _cultivo("URETRAL", "Cultivo uretral")
        base = dict(
            paciente=self.paciente, medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA", estado="RECIBIDO",
        )
        self.uro = EstudioMicrobiologia.objects.create(tipo_cultivo=uro, tipo_estudio="UROCULTIVO", **base)
        self.hemoc = EstudioMicrobiologia.objects.create(tipo_cultivo=hemo_c, tipo_estudio="HEMOCULTIVO", **base)
        self.uretral = EstudioMicrobiologia.objects.create(tipo_cultivo=uretral, tipo_estudio="URETRAL", **base)
        self.uro_otro_pac = EstudioMicrobiologia.objects.create(
            paciente=self.paciente2, medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA", estado="RECIBIDO",
            tipo_cultivo=uro, tipo_estudio="UROCULTIVO",
        )

    def _items(self, *pares):
        return [{"tipo": t, "id": i} for t, i in pares]

    def test_pedido_clinico_marca_panel_y_examen_y_otros(self):
        ped = construir_pedido_clinico(self.sol)
        self.assertIn("PAN_HEMO", ped.marcados)
        self.assertIn("GLU", ped.marcados)
        # Componente del panel: no se marca suelto ni va a "Otro".
        self.assertNotIn("HGB", ped.marcados)
        self.assertEqual(ped.otros, ["Examen fuera de formulario"])
        self.assertEqual(ped.datos.obra_social, "OSDE")
        self.assertEqual(ped.datos.afiliado, "123/45")
        self.assertIn("García", ped.datos.medico)

    def test_pedido_micro_mapea_cultivos_y_cultivo_de(self):
        ped = construir_pedido_micro([self.uro, self.hemoc, self.uretral])
        self.assertIn("UROCULTIVO", ped.marcados)
        self.assertIn("HEMOCULTIVO", ped.marcados)
        self.assertIn(MICRO_CULTIVO_DE, ped.marcados)
        self.assertEqual(ped.cultivo_de, ["uretral"])

    def test_micro_agrupado_por_paciente_dos_pedidos_por_hoja(self):
        items = parsear_items(self._items(
            ("LAB_CLINICO", self.sol.pk),
            ("MICROBIOLOGIA", self.uro.pk),
            ("MICROBIOLOGIA", self.uro_otro_pac.pk),
            ("MICROBIOLOGIA", self.hemoc.pk),
        ))
        pdf, pedidos = generar_pedidos_papel_pdf_bytes(items)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(pedidos, 3)
        self.assertEqual(_paginas(pdf), 2)

    def test_parsear_items_valida(self):
        with self.assertRaises(ImpresionOrdenesError):
            parsear_items([])
        with self.assertRaises(ImpresionOrdenesError):
            parsear_items([{"tipo": "OTRO", "id": 1}])
        items = parsear_items(self._items(("LAB_CLINICO", 3), ("LAB_CLINICO", 3)))
        self.assertEqual(len(items), 1)

    def test_api_pedidos_pdf_200_y_auditoria_sin_mutar_estado(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                URL_PEDIDOS,
                {"items": self._items(("LAB_CLINICO", self.sol.pk), ("MICROBIOLOGIA", self.uro.pk))},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.sol.refresh_from_db()
        self.assertEqual(self.sol.estado, "EN_PROCESO")
        self.assertTrue(
            AuditEvent.objects.filter(metadata__accion="lims_pedidos_papel_pdf").exists()
        )

    def test_api_listado_dia_pdf_200(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            URL_LISTADO,
            {
                "fecha": "2026-09-30",
                "items": self._items(("LAB_CLINICO", self.sol.pk), ("MICROBIOLOGIA", self.uro.pk)),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_api_sin_items_400(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(URL_PEDIDOS, {"items": []}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resena_solo_para_examenes_fuera_del_listado_basico(self):
        ped = construir_pedido_clinico(self.sol)
        self.assertEqual([n for _, n in ped.resena_examenes], ["Examen fuera de formulario"])
        sol_basica = SolicitudExamen.objects.create(
            paciente=self.paciente, medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO",
        )
        sol_basica.tipos_examen.add(self.glu, self.hgb)
        self.assertEqual(construir_pedido_clinico(sol_basica).resena_examenes, [])

    def test_resena_reglas_usa_sexo_edad_antecedentes_y_dx(self):
        texto = construir_resena_reglas(ContextoResena(
            sexo="F", edad=70, antecedentes="hipertensión arterial",
            diagnostico="Fibrilación auricular",
            examenes=[("TSH", "TSH"), ("T4L", "T4L"), ("PSA", "PSA")],
        ))
        self.assertIn("Paciente femenina de 70 años", texto)
        self.assertIn("antecedentes de hipertensión arterial", texto)
        self.assertIn("diagnóstico de Fibrilación auricular", texto)
        self.assertIn("TSH y T4L para descartar disfunción tiroidea", texto)
        self.assertIn("PSA para control prostático", texto)

    def test_probnp_agrega_dos_formularios_en_hoja_propia(self):
        tm = self.glu.tipo_muestra_requerida
        probnp = _examen("PROBNP", "Pro-BNP", tm)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente2, medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.glu, probnp)
        ped = construir_pedido_clinico(sol)
        self.assertTrue(ped.incluye_probnp)
        self.assertEqual(ped.resena_examenes, [])
        pdf, pedidos = generar_pedidos_papel_pdf_bytes(parsear_items(self._items(("LAB_CLINICO", sol.pk))))
        self.assertEqual(pedidos, 1)
        # Pedido solo en la 1ª hoja; los 2 de proBNP juntos en la 2ª.
        self.assertEqual(_paginas(pdf), 2)

    def test_api_resenas_sugeridas_y_pdf_con_texto_revisado(self):
        self.client.force_authenticate(self.lab)
        items = self._items(("LAB_CLINICO", self.sol.pk), ("MICROBIOLOGIA", self.uro.pk))
        with self.settings(MEDGEMMA_ENABLED=False):
            r = self.client.post(URL_RESENAS, {"items": items}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        resenas = r.json()["resenas"]
        self.assertEqual(len(resenas), 1)
        self.assertEqual(resenas[0]["solicitud_id"], self.sol.pk)
        self.assertEqual(resenas[0]["fuente"], "reglas")
        self.assertIn("Examen fuera de formulario", resenas[0]["texto"])

        r = self.client.post(
            URL_PEDIDOS,
            {"items": items, "resenas": [{"solicitud_id": self.sol.pk, "texto": "Texto revisado."}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_parsear_resenas_valida(self):
        self.assertEqual(parsear_resenas(None), {})
        self.assertEqual(parsear_resenas([{"solicitud_id": 4, "texto": " a "}]), {4: "a"})
        with self.assertRaises(ImpresionOrdenesError):
            parsear_resenas([{"solicitud_id": "x", "texto": "a"}])
        with self.assertRaises(ImpresionOrdenesError):
            parsear_resenas([{"solicitud_id": 1, "texto": "a" * 2001}])

    def test_api_medico_403(self):
        self.client.force_authenticate(self.med_user)
        r = self.client.post(
            URL_LISTADO,
            {"items": self._items(("LAB_CLINICO", self.sol.pk))},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
