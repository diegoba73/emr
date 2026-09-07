"""
Tests focales: etiqueta ZPL 40×23 mm por Muestra (3nStar LDT114).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.label_printer_transport import (
    LabelPrinterConfig,
    LabelPrinterError,
    send_zpl_to_network_printer,
)
from laboratorio.label_zpl import (
    MAX_CONTENT_WIDTH_DOTS,
    CodigoBarraZplError,
    build_label_lines,
    escape_zpl_fd,
    estimated_text_width_dots,
    format_paciente_abreviado,
    max_font_width_for_text,
    prepare_codigo_barra_for_zpl,
    render_zpl_40x23,
)
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra, TipoContenedor
from laboratorio.muestra_estado import aplicar_cambiar_ubicacion, aplicar_tomar, crear_muestra
from laboratorio.services_etiqueta_muestra import (
    EtiquetaMuestraError,
    build_etiqueta_muestra,
    imprimir_etiqueta_muestra,
    tipo_operacional_imprimible,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestLabelZplRenderer(TestCase):
    def test_dimensiones_y_cuatro_lineas_con_ancho(self):
        from django.utils.timezone import make_aware

        self.assertEqual(MAX_CONTENT_WIDTH_DOTS, 296)
        dt = make_aware(datetime(2026, 9, 7, 14, 5, 0))
        lines = build_label_lines(
            codigo_barra="00458127",
            apellido="Perez",
            nombre="Juan",
            dni="23123456",
            lugar_extraccion="guardia",
            fecha_toma=dt,
            tipo_operacional="EDTA",
        )
        self.assertEqual(lines.as_list(), [
            "00458127",
            "PEREZ J. | DNI 23123456",
            "GUARDIA",
            "07/09 14:05 | EDTA",
        ])
        rendered = render_zpl_40x23(lines)
        self.assertIn("^PW320", rendered.zpl)
        self.assertIn("^LL184", rendered.zpl)
        self.assertTrue(rendered.zpl.strip().startswith("^XA"))
        self.assertTrue(rendered.zpl.strip().endswith("^XZ"))
        self.assertEqual(rendered.zpl.count("^FD"), 4)
        self.assertTrue(rendered.all_fit_width())
        # Ejemplo corto: código 8 chars → w preferido 28 cabe (8*28=224≤296).
        self.assertEqual(rendered.layouts[0].text, "00458127")
        self.assertEqual(rendered.layouts[0].width, 28)
        self.assertEqual(rendered.layouts[0].estimated_width_dots, 8 * 28)
        # Paciente 25 chars: w = min(18, 296//25)=11 → 25*11=275≤296.
        self.assertEqual(rendered.layouts[1].text, "PEREZ J. | DNI 23123456")
        self.assertEqual(rendered.layouts[1].width, max_font_width_for_text(
            rendered.layouts[1].text, preferred=18
        ))
        self.assertLessEqual(rendered.layouts[1].estimated_width_dots, MAX_CONTENT_WIDTH_DOTS)
        self.assertLessEqual(rendered.layouts[3].estimated_width_dots, MAX_CONTENT_WIDTH_DOTS)

    def test_codigo_lab_real_sin_truncar_y_cabe(self):
        codigo = "LAB-2026-00001-01"
        self.assertEqual(len(codigo), 17)
        lines = build_label_lines(
            codigo_barra=codigo,
            apellido="Perez",
            nombre="Juan",
            dni="23123456",
            lugar_extraccion="GUARDIA",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        self.assertEqual(lines.codigo, codigo)  # sin truncar
        rendered = render_zpl_40x23(lines)
        self.assertEqual(rendered.layouts[0].text, codigo)
        # 17 * w ≤ 296 → w máx 17 (296//17)
        self.assertEqual(rendered.layouts[0].width, 17)
        self.assertEqual(rendered.layouts[0].estimated_width_dots, 17 * 17)
        self.assertLessEqual(rendered.layouts[0].estimated_width_dots, MAX_CONTENT_WIDTH_DOTS)
        self.assertTrue(rendered.all_fit_width())
        self.assertIn(f"^A0N,{rendered.layouts[0].height},17^FD{codigo}^FS", rendered.zpl)

    def test_codigo_max_length_32_sin_truncar(self):
        codigo32 = "L" + "A" * 30 + "B"
        self.assertEqual(len(codigo32), 32)
        lines = build_label_lines(
            codigo_barra=codigo32,
            apellido="X",
            nombre="Y",
            dni="1",
            lugar_extraccion="G",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        self.assertEqual(lines.codigo, codigo32)
        rendered = render_zpl_40x23(lines)
        self.assertEqual(rendered.layouts[0].text, codigo32)
        self.assertEqual(rendered.layouts[0].width, 296 // 32)  # 9
        self.assertLessEqual(rendered.layouts[0].estimated_width_dots, MAX_CONTENT_WIDTH_DOTS)

    def test_apellido_largo_dni_intacto_y_ancho(self):
        lines = build_label_lines(
            codigo_barra="LAB-2026-00002-03",
            apellido="Apellidolarguisimoextraordinario",
            nombre="Pedro",
            dni="30111222",
            lugar_extraccion="UCI-3",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        self.assertIn("DNI 30111222", lines.paciente_dni)
        self.assertTrue(lines.paciente_dni.endswith("DNI 30111222"))
        rendered = render_zpl_40x23(lines)
        self.assertLessEqual(rendered.layouts[1].estimated_width_dots, MAX_CONTENT_WIDTH_DOTS)
        self.assertTrue(rendered.all_fit_width())
        again = build_label_lines(
            codigo_barra="LAB-2026-00002-03",
            apellido="Apellidolarguisimoextraordinario",
            nombre="Pedro",
            dni="30111222",
            lugar_extraccion="UCI-3",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        self.assertEqual(lines.paciente_dni, again.paciente_dni)

    def test_fecha_edta_cabe(self):
        from django.utils.timezone import make_aware

        dt = make_aware(datetime(2026, 9, 7, 14, 5, 0))
        lines = build_label_lines(
            codigo_barra="00458127",
            apellido="Perez",
            nombre="J",
            dni="23123456",
            lugar_extraccion="GUARDIA",
            fecha_toma=dt,
            tipo_operacional="EDTA",
        )
        self.assertEqual(lines.fecha_tipo, "07/09 14:05 | EDTA")
        rendered = render_zpl_40x23(lines)
        lay4 = rendered.layouts[3]
        self.assertEqual(lay4.text, "07/09 14:05 | EDTA")
        self.assertLessEqual(lay4.estimated_width_dots, MAX_CONTENT_WIDTH_DOTS)
        self.assertEqual(
            lay4.width,
            max_font_width_for_text(lay4.text, preferred=16),
        )

    def test_paciente_abreviado_y_lugares(self):
        self.assertEqual(format_paciente_abreviado("Nuñez", "María"), "NUÑEZ M.")
        lines = build_label_lines(
            codigo_barra="LAB-2026-00001-01",
            apellido="Gonzalez",
            nombre="Ana",
            dni="1234567",
            lugar_extraccion="cama 12",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        self.assertIn("CAMA 12", lines.lugar)
        self.assertIn("DNI 1234567", lines.paciente_dni)
        rendered = render_zpl_40x23(lines)
        self.assertTrue(rendered.all_fit_width())

    def test_escape_zpl_injection(self):
        dirty = "PEREZ^XA ~JA GUARDIA^XZ"
        safe = escape_zpl_fd(dirty)
        self.assertNotIn("^", safe)
        self.assertNotIn("~", safe)
        lines = build_label_lines(
            codigo_barra="SAFE01",
            apellido="PEREZ^XA",
            nombre="A",
            dni="111",
            lugar_extraccion="GUARDIA^XZ",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        rendered = render_zpl_40x23(lines)
        self.assertEqual(rendered.zpl.count("^XA"), 1)
        self.assertEqual(rendered.zpl.count("^XZ"), 1)
        self.assertNotIn("^FDPEREZ^XA", rendered.zpl)
        self.assertTrue(rendered.all_fit_width())

    def test_determinismo_mismo_contenido(self):
        dt = timezone.now()
        a = build_label_lines(
            codigo_barra="C1",
            apellido="Lopez",
            nombre="I",
            dni="99",
            lugar_extraccion="GUARDIA",
            fecha_toma=dt,
            tipo_operacional="EDTA",
        )
        b = build_label_lines(
            codigo_barra="C1",
            apellido="Lopez",
            nombre="I",
            dni="99",
            lugar_extraccion="GUARDIA",
            fecha_toma=dt,
            tipo_operacional="EDTA",
        )
        ra, rb = render_zpl_40x23(a), render_zpl_40x23(b)
        self.assertEqual(ra.zpl, rb.zpl)
        self.assertEqual(
            [lay.width for lay in ra.layouts],
            [lay.width for lay in rb.layouts],
        )

    def test_estimated_width_helper(self):
        self.assertEqual(estimated_text_width_dots("ABCD", 10), 40)
        self.assertEqual(max_font_width_for_text("ABCD", preferred=40), 40)  # 4*40=160≤296
        self.assertEqual(max_font_width_for_text("A" * 30, preferred=28), 9)  # 296//30


@pytest.mark.django_db
class TestEtiquetaMuestraApi(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_ez_{self.suf}",
            email=f"lez{self.suf}@t.com",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_ez_{self.suf}",
            email=f"aez{self.suf}@t.com",
            password="pass12345",
            rol="admin",
            is_staff=True,
        )
        self.su = User.objects.create_superuser(
            username=f"su_ez_{self.suf}",
            email=f"sez{self.suf}@t.com",
            password="pass12345",
        )
        self.med = User.objects.create_user(
            username=f"med_ez_{self.suf}",
            email=f"mez{self.suf}@t.com",
            password="pass12345",
            rol="medico",
        )
        self.sec = User.objects.create_user(
            username=f"sec_ez_{self.suf}",
            email=f"sez2{self.suf}@t.com",
            password="pass12345",
            rol="secretaria",
        )
        self.enf = User.objects.create_user(
            username=f"enf_ez_{self.suf}",
            email=f"eez{self.suf}@t.com",
            password="pass12345",
            rol="enfermeria",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_ez_{self.suf}",
            email=f"pez{self.suf}@t.com",
            password="pass12345",
            rol="paciente",
        )
        esp = Especialidad.objects.create(nombre=f"Esp {self.suf}")
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Ez",
            matricula=f"EZ{self.suf}",
            especialidad=esp,
            user=self.med,
        )
        self.paciente = Paciente.objects.create(
            dni=f"23123456{self.suf[:2]}",
            nombre="Juan",
            apellido="Perez",
            user=self.pac_u,
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"SM{self.suf}"[:10],
            nombre="Sangre EDTA",
            activo=True,
        )
        self.tc = TipoContenedor.objects.create(
            codigo=f"ED{self.suf}"[:10],
            nombre="Tubo EDTA",
            aditivo="EDTA K2",
            activo=True,
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GL{self.suf}"[:10],
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        self.solicitud.tipos_examen.add(self.te)
        self.client = APIClient(enforce_csrf_checks=False)

    def _muestra_lista(self) -> Muestra:
        m = crear_muestra(
            solicitud=self.solicitud,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=self.tc.pk,
            observaciones="",
            actor=self.lab,
            view="test",
        )
        aplicar_tomar(
            m.pk,
            actor=self.lab,
            view="test",
            lugar_extraccion="GUARDIA",
        )
        m.refresh_from_db()
        return m

    def test_tipo_operacional_usa_aditivo_edta(self):
        m = self._muestra_lista()
        self.assertEqual(tipo_operacional_imprimible(m), "EDTA")

    def test_tomar_guarda_lugar_y_cambiar_ubicacion_no_lo_pisa(self):
        m = crear_muestra(
            solicitud=self.solicitud,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=self.tc.pk,
            observaciones="",
            actor=self.lab,
            view="test",
        )
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            f"/api/lab/muestras-transaccionales/{m.pk}/tomar/",
            {"lugar_extraccion": "cama 12"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "CAMA 12")
        from laboratorio.muestra_estado import aplicar_recibir

        aplicar_recibir(
            m.pk,
            actor=self.lab,
            view="test",
            ubicacion_actual="Recepción",
        )
        aplicar_cambiar_ubicacion(
            m.pk,
            actor=self.lab,
            view="test",
            ubicacion_actual="Rack 9",
        )
        m.refresh_from_db()
        self.assertEqual(m.ubicacion_actual, "Rack 9")
        self.assertEqual(m.lugar_extraccion, "CAMA 12")

    def test_tomar_vacio_sigue_compat(self):
        m = crear_muestra(
            solicitud=self.solicitud,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=self.tc.pk,
            observaciones="",
            actor=self.lab,
            view="test",
        )
        self.client.force_authenticate(self.lab)
        r = self.client.post(f"/api/lab/muestras-transaccionales/{m.pk}/tomar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        m.refresh_from_db()
        self.assertEqual(m.estado, "TOMADA")
        self.assertFalse(m.lugar_extraccion)

    def test_preview_y_permisos(self):
        m = self._muestra_lista()
        url = f"/api/lab/muestras-transaccionales/{m.pk}/etiqueta-zpl/"
        for user in (self.lab, self.admin, self.su):
            self.client.force_authenticate(user)
            r = self.client.get(url)
            self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
            body = r.json()
            self.assertTrue(body["printable"])
            self.assertEqual(len(body["lines"]), 4)
            self.assertIn("^PW320", body["zpl"])
            self.assertEqual(body["profile"], "3nstar_ldt114_203_40x23")

        for user in (self.med, self.sec, self.enf, self.pac_u):
            self.client.force_authenticate(user)
            r = self.client.get(url)
            self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(None)
        r = self.client.get(url)
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_preview_sin_toma_no_printable(self):
        m = crear_muestra(
            solicitud=self.solicitud,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=self.tc.pk,
            observaciones="",
            actor=self.lab,
            view="test",
        )
        self.client.force_authenticate(self.lab)
        r = self.client.get(f"/api/lab/muestras-transaccionales/{m.pk}/etiqueta-zpl/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        body = r.json()
        self.assertFalse(body["printable"])
        self.assertEqual(body["zpl"], "")
        self.assertTrue(body["validation_errors"])

    def test_imprimir_sin_lugar_400(self):
        m = crear_muestra(
            solicitud=self.solicitud,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=self.tc.pk,
            observaciones="",
            actor=self.lab,
            view="test",
        )
        aplicar_tomar(m.pk, actor=self.lab, view="test", lugar_extraccion="")
        self.client.force_authenticate(self.lab)
        r = self.client.post(f"/api/lab/muestras-transaccionales/{m.pk}/imprimir-etiqueta/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("zpl", (r.json().get("error") or "").lower())

    def test_imprimir_paciente_legacy_incompleto(self):
        self.paciente.apellido = ""
        self.paciente.save(update_fields=["apellido"])
        m = self._muestra_lista()
        with self.assertRaises(EtiquetaMuestraError):
            build_etiqueta_muestra(m, require_printable=True)

    @override_settings(LIMS_LABEL_PRINTER_ENABLED=False)
    def test_imprimir_disabled_503(self):
        m = self._muestra_lista()
        self.client.force_authenticate(self.lab)
        r = self.client.post(f"/api/lab/muestras-transaccionales/{m.pk}/imprimir-etiqueta/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("no configurada", r.json()["error"].lower())
        self.assertFalse(
            AuditEvent.objects.filter(metadata__accion="muestra_etiqueta_print").exists()
        )

    @override_settings(
        LIMS_LABEL_PRINTER_ENABLED=True,
        LIMS_LABEL_PRINTER_HOST="127.0.0.1",
        LIMS_LABEL_PRINTER_PORT=9100,
    )
    def test_imprimir_ok_audita_sin_phi(self):
        m = self._muestra_lista()
        self.client.force_authenticate(self.lab)
        with mock.patch(
            "laboratorio.services_etiqueta_muestra.send_zpl_to_network_printer"
        ) as send:
            with self.captureOnCommitCallbacks(execute=True):
                r = self.client.post(
                    f"/api/lab/muestras-transaccionales/{m.pk}/imprimir-etiqueta/",
                    {},
                    format="json",
                )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        send.assert_called_once()
        body = r.json()
        self.assertEqual(body["resultado"], "ok")
        self.assertNotIn("zpl", body)
        self.assertNotIn("lines", body)

        ev = AuditEvent.objects.filter(metadata__accion="muestra_etiqueta_print").latest("id")
        meta = ev.metadata or {}
        blob = str(meta) + str(ev.before_state) + str(ev.after_state) + (ev.entity_repr or "")
        self.assertEqual(meta.get("muestra_id"), m.pk)
        self.assertEqual(meta.get("solicitud_id"), m.solicitud_id)
        self.assertNotIn(m.codigo_barra or "___", blob)
        self.assertNotIn(self.paciente.dni, blob)
        self.assertNotIn("Perez", blob)
        self.assertNotIn("PEREZ", blob)
        self.assertNotIn("GUARDIA", blob)
        self.assertNotIn("^XA", blob)

        # Reimpresión = segundo evento
        with mock.patch(
            "laboratorio.services_etiqueta_muestra.send_zpl_to_network_printer"
        ):
            with self.captureOnCommitCallbacks(execute=True):
                r2 = self.client.post(
                    f"/api/lab/muestras-transaccionales/{m.pk}/imprimir-etiqueta/",
                    {},
                    format="json",
                )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            AuditEvent.objects.filter(metadata__accion="muestra_etiqueta_print").count(),
            2,
        )

    def test_medico_no_imprime(self):
        m = self._muestra_lista()
        self.client.force_authenticate(self.med)
        r = self.client.post(
            f"/api/lab/muestras-transaccionales/{m.pk}/imprimir-etiqueta/",
            {},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_muestra_inexistente_sin_phi(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/lab/muestras-transaccionales/99999991/etiqueta-zpl/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn("Perez", str(r.content))

    def test_legacy_solicitud_etiqueta_intacta(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get(f"/api/lab/solicitudes/{self.solicitud.pk}/etiqueta/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("zpl", r.json())

    def test_alias_laboratorio_etiqueta_zpl(self):
        m = self._muestra_lista()
        self.client.force_authenticate(self.lab)
        r = self.client.get(f"/api/laboratorio/muestras-transaccionales/{m.pk}/etiqueta-zpl/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestLabelPrinterTransport(TestCase):
    def test_disabled(self):
        cfg = LabelPrinterConfig(
            enabled=False, host="10.0.0.1", port=9100, timeout_seconds=1, profile_key="x"
        )
        with self.assertRaises(LabelPrinterError) as ctx:
            send_zpl_to_network_printer("^XA^XZ", config=cfg)
        self.assertEqual(ctx.exception.code, "printer_disabled")

    def test_missing_host(self):
        cfg = LabelPrinterConfig(
            enabled=True, host="", port=9100, timeout_seconds=1, profile_key="x"
        )
        with self.assertRaises(LabelPrinterError) as ctx:
            send_zpl_to_network_printer("^XA^XZ", config=cfg)
        self.assertEqual(ctx.exception.code, "printer_misconfigured")

    def test_send_ok_closes_socket(self):
        cfg = LabelPrinterConfig(
            enabled=True, host="127.0.0.1", port=9100, timeout_seconds=2, profile_key="x"
        )
        mock_sock = mock.MagicMock()
        with mock.patch("socket.create_connection", return_value=mock_sock) as conn:
            send_zpl_to_network_printer("^XA^XZ", config=cfg)
        conn.assert_called_once_with(("127.0.0.1", 9100), timeout=2)
        mock_sock.sendall.assert_called_once()
        mock_sock.close.assert_called_once()

    def test_timeout_no_retry(self):
        cfg = LabelPrinterConfig(
            enabled=True, host="127.0.0.1", port=9100, timeout_seconds=1, profile_key="x"
        )
        with mock.patch("socket.create_connection", side_effect=TimeoutError("t")) as conn:
            with self.assertRaises(LabelPrinterError) as ctx:
                send_zpl_to_network_printer("^XA^XZ", config=cfg)
        self.assertEqual(ctx.exception.code, "printer_timeout")
        self.assertEqual(conn.call_count, 1)

    def test_connection_refused_no_retry(self):
        cfg = LabelPrinterConfig(
            enabled=True, host="127.0.0.1", port=9100, timeout_seconds=1, profile_key="x"
        )
        with mock.patch(
            "socket.create_connection", side_effect=ConnectionRefusedError()
        ) as conn:
            with self.assertRaises(LabelPrinterError) as ctx:
                send_zpl_to_network_printer("^XA^XZ", config=cfg)
        self.assertEqual(ctx.exception.code, "printer_unreachable")
        self.assertEqual(conn.call_count, 1)

    @override_settings(
        LIMS_LABEL_PRINTER_ENABLED=True,
        LIMS_LABEL_PRINTER_HOST="127.0.0.1",
        LIMS_LABEL_PRINTER_PORT=9100,
    )
    def test_imprimir_timeout_no_audit_success(self):
        suf = uuid.uuid4().hex[:8]
        lab = User.objects.create_user(
            username=f"lab_to_{suf}",
            email=f"lto{suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        pac = Paciente.objects.create(dni=f"DNI{suf}", nombre="A", apellido="B")
        tm = TipoMuestra.objects.create(codigo=f"T{suf}"[:10], nombre="S", activo=True)
        tc = TipoContenedor.objects.create(
            codigo=f"C{suf}"[:10], nombre="EDTA", aditivo="EDTA", activo=True
        )
        sol = SolicitudExamen.objects.create(
            paciente=pac,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=tm.pk,
            tipo_contenedor_id=tc.pk,
            observaciones="",
            actor=lab,
            view="t",
        )
        aplicar_tomar(m.pk, actor=lab, view="t", lugar_extraccion="GUARDIA")
        m.refresh_from_db()
        with mock.patch(
            "laboratorio.services_etiqueta_muestra.send_zpl_to_network_printer",
            side_effect=LabelPrinterError("printer_timeout", "fail"),
        ):
            with self.assertRaises(LabelPrinterError):
                imprimir_etiqueta_muestra(m, actor=lab, view="t")
        self.assertFalse(
            AuditEvent.objects.filter(metadata__accion="muestra_etiqueta_print").exists()
        )


@pytest.mark.django_db
class TestLugarExtraccionSnapshot(TestCase):
    """B1: lugar_extraccion es snapshot de toma / legacy controlado."""

    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_lug_{self.suf}",
            email=f"ll{self.suf}@t.com",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        self.pac = Paciente.objects.create(
            nombre="Ana", apellido="Lopez", dni=f"3{self.suf[:7]}"
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"T{self.suf[:6]}", nombre="Sangre", activo=True
        )
        self.tc = TipoContenedor.objects.create(
            codigo=f"C{self.suf[:6]}", nombre="EDTA", aditivo="EDTA K2", activo=True
        )
        self.te = TipoExamen.objects.create(
            codigo=f"E{self.suf[:6]}",
            nombre="Glu",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac, origen_solicitud="GUARDIA", estado="PENDIENTE"
        )
        self.sol.tipos_examen.add(self.te)
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def _pendiente(self) -> Muestra:
        return crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=self.tc.pk,
            observaciones="",
            actor=self.lab,
            view="test",
        )

    def test_patch_lugar_antes_de_toma_rechazado(self):
        m = self._pendiente()
        r = self.client.patch(
            f"/api/lab/muestras-transaccionales/{m.pk}/",
            {"lugar_extraccion": "GUARDIA"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.content)
        m.refresh_from_db()
        self.assertFalse(m.lugar_extraccion)

    def test_tomar_guarda_lugar(self):
        m = self._pendiente()
        r = self.client.post(
            f"/api/lab/muestras-transaccionales/{m.pk}/tomar/",
            {"lugar_extraccion": "GUARDIA"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "GUARDIA")

    def test_patch_posterior_con_snapshot_rechazado(self):
        m = self._pendiente()
        self.client.post(
            f"/api/lab/muestras-transaccionales/{m.pk}/tomar/",
            {"lugar_extraccion": "GUARDIA"},
            format="json",
        )
        r = self.client.patch(
            f"/api/lab/muestras-transaccionales/{m.pk}/",
            {"lugar_extraccion": "UCI"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.content)
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "GUARDIA")

    def test_legacy_tomada_sin_lugar_permite_una_vez(self):
        m = self._pendiente()
        aplicar_tomar(m.pk, actor=self.lab, view="test", lugar_extraccion="")
        m.refresh_from_db()
        self.assertFalse(m.lugar_extraccion)
        r = self.client.patch(
            f"/api/lab/muestras-transaccionales/{m.pk}/",
            {"lugar_extraccion": "UCI-3"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "UCI-3")
        r2 = self.client.patch(
            f"/api/lab/muestras-transaccionales/{m.pk}/",
            {"lugar_extraccion": "OTRO"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "UCI-3")

    def test_segunda_actualizacion_atomica_no_sobrescribe(self):
        m = self._pendiente()
        aplicar_tomar(m.pk, actor=self.lab, view="test", lugar_extraccion="")
        from django.db.models import Q
        from laboratorio.models_catalog import Muestra as M

        n1 = (
            M.objects.filter(pk=m.pk, fecha_toma__isnull=False)
            .filter(Q(lugar_extraccion__isnull=True) | Q(lugar_extraccion=""))
            .update(lugar_extraccion="PRIMERO")
        )
        n2 = (
            M.objects.filter(pk=m.pk, fecha_toma__isnull=False)
            .filter(Q(lugar_extraccion__isnull=True) | Q(lugar_extraccion=""))
            .update(lugar_extraccion="SEGUNDO")
        )
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 0)
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "PRIMERO")

    def test_tomar_no_desplazado_por_patch_previo(self):
        m = self._pendiente()
        self.client.patch(
            f"/api/lab/muestras-transaccionales/{m.pk}/",
            {"lugar_extraccion": "ANTICIPADO"},
            format="json",
        )
        m.refresh_from_db()
        self.assertFalse(m.lugar_extraccion)
        self.client.post(
            f"/api/lab/muestras-transaccionales/{m.pk}/tomar/",
            {"lugar_extraccion": "GUARDIA"},
            format="json",
        )
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "GUARDIA")

    def test_stale_patch_no_borra_lugar_completado(self):
        """save() con update_fields: PATCH concurrente no reescribe snapshot."""
        m = self._pendiente()
        aplicar_tomar(m.pk, actor=self.lab, view="test", lugar_extraccion="GUARDIA")
        m.refresh_from_db()
        # Instancia stale en memoria (como un request largo).
        stale = Muestra.objects.get(pk=m.pk)
        stale.lugar_extraccion = ""
        stale.observaciones = "obs concurrente"
        from laboratorio.serializers_muestras import MuestraPartialUpdateSerializer

        ser = MuestraPartialUpdateSerializer(
            instance=stale,
            data={"observaciones": "obs concurrente"},
            partial=True,
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()
        m.refresh_from_db()
        self.assertEqual(m.lugar_extraccion, "GUARDIA")
        self.assertEqual(m.observaciones, "obs concurrente")

    def test_lugar_mas_campo_invalido_rollback(self):
        """Si el PATCH falla, el lugar legacy no debe quedar parcial."""
        m = self._pendiente()
        aplicar_tomar(m.pk, actor=self.lab, view="test", lugar_extraccion="")
        m.refresh_from_db()
        # tipo_contenedor inexistente → 400; lugar no debe persistir.
        r = self.client.patch(
            f"/api/lab/muestras-transaccionales/{m.pk}/",
            {"lugar_extraccion": "UCI", "tipo_contenedor": 99999991},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.content)
        m.refresh_from_db()
        self.assertFalse(m.lugar_extraccion)


@pytest.mark.django_db
class TestCodigoBarraZplIdentity(TestCase):
    """B2: codigo_barra nunca se transforma silenciosamente."""

    def test_codigo_normal_identico_en_lines_y_zpl(self):
        codigo = "LAB-2026-00042-01"
        lines = build_label_lines(
            codigo_barra=codigo,
            apellido="Perez",
            nombre="Juan",
            dni="23123456",
            lugar_extraccion="GUARDIA",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        rendered = render_zpl_40x23(lines)
        self.assertEqual(lines.codigo, codigo)
        self.assertEqual(rendered.layouts[0].text, codigo)
        self.assertIn(f"^FD{codigo}^FS", rendered.zpl)

    def test_codigo_inseguro_rechaza_sin_transformar(self):
        cases = (
            "LAB^01",
            "LAB~01",
            "LAB\\01",
            "LAB\t01",
            "LAB\n01",
            "LAB\r01",
            "\tLAB01",
            "LAB01\n",
            " LAB01",
            "LAB01 ",
        )
        for dirty in cases:
            with self.subTest(dirty=repr(dirty)):
                with self.assertRaises(CodigoBarraZplError):
                    prepare_codigo_barra_for_zpl(dirty)
                with self.assertRaises(CodigoBarraZplError):
                    build_label_lines(
                        codigo_barra=dirty,
                        apellido="Perez",
                        nombre="J",
                        dni="1",
                        lugar_extraccion="G",
                        fecha_toma=timezone.now(),
                        tipo_operacional="EDTA",
                    )

    def test_lugar_solo_metacaracteres_no_printable(self):
        suf = uuid.uuid4().hex[:8]
        lab = User.objects.create_user(
            username=f"lab_lug2_{suf}",
            email=f"lg2{suf}@t.com",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        pac = Paciente.objects.create(nombre="A", apellido="B", dni=f"5{suf[:7]}")
        tm = TipoMuestra.objects.create(codigo=f"T{suf[:6]}", nombre="S", activo=True)
        tc = TipoContenedor.objects.create(
            codigo=f"C{suf[:6]}", nombre="E", aditivo="EDTA", activo=True
        )
        te = TipoExamen.objects.create(
            codigo=f"E{suf[:6]}",
            nombre="X",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            activo=True,
        )
        sol = SolicitudExamen.objects.create(
            paciente=pac, origen_solicitud="GUARDIA", estado="PENDIENTE"
        )
        sol.tipos_examen.add(te)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=tm.pk,
            tipo_contenedor_id=tc.pk,
            observaciones="",
            actor=lab,
            view="t",
        )
        aplicar_tomar(m.pk, actor=lab, view="t", lugar_extraccion="GUARDIA")
        m.refresh_from_db()
        Muestra.objects.filter(pk=m.pk).update(lugar_extraccion="^~")
        m.refresh_from_db()
        payload = build_etiqueta_muestra(m)
        self.assertFalse(payload.printable)
        self.assertEqual(payload.zpl, "")
        self.assertTrue(any("lugar" in e.lower() for e in payload.validation_errors))
        with mock.patch(
            "laboratorio.services_etiqueta_muestra.send_zpl_to_network_printer"
        ) as send:
            with self.assertRaises(EtiquetaMuestraError):
                imprimir_etiqueta_muestra(m, actor=lab, view="t")
            send.assert_not_called()

    def test_preview_lines_igual_fd_zpl(self):
        lines = build_label_lines(
            codigo_barra="SAFE-99",
            apellido="PEREZ^XA",
            nombre="A",
            dni="111",
            lugar_extraccion="GUARDIA^XZ",
            fecha_toma=timezone.now(),
            tipo_operacional="EDTA",
        )
        rendered = render_zpl_40x23(lines)
        for expected, lay in zip(lines.as_list(), rendered.layouts, strict=True):
            self.assertEqual(expected, lay.text)
            self.assertIn(f"^FD{lay.text}^FS", rendered.zpl)
        self.assertEqual(rendered.zpl.count("^XA"), 1)
        self.assertEqual(rendered.zpl.count("^XZ"), 1)

    def test_api_codigo_inseguro_no_printable(self):
        suf = uuid.uuid4().hex[:8]
        lab = User.objects.create_user(
            username=f"lab_cb_{suf}",
            email=f"cb{suf}@t.com",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        pac = Paciente.objects.create(nombre="A", apellido="B", dni=f"4{suf[:7]}")
        tm = TipoMuestra.objects.create(codigo=f"T{suf[:6]}", nombre="S", activo=True)
        tc = TipoContenedor.objects.create(
            codigo=f"C{suf[:6]}", nombre="E", aditivo="EDTA", activo=True
        )
        te = TipoExamen.objects.create(
            codigo=f"E{suf[:6]}",
            nombre="X",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            activo=True,
        )
        sol = SolicitudExamen.objects.create(
            paciente=pac, origen_solicitud="GUARDIA", estado="PENDIENTE"
        )
        sol.tipos_examen.add(te)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=tm.pk,
            tipo_contenedor_id=tc.pk,
            observaciones="",
            actor=lab,
            view="t",
        )
        aplicar_tomar(m.pk, actor=lab, view="t", lugar_extraccion="GUARDIA")
        m.refresh_from_db()
        Muestra.objects.filter(pk=m.pk).update(codigo_barra="BAD^CODE")
        m.refresh_from_db()
        payload = build_etiqueta_muestra(m)
        self.assertFalse(payload.printable)
        self.assertEqual(payload.zpl, "")
        self.assertTrue(
            any("fiel" in e.lower() or "zpl" in e.lower() for e in payload.validation_errors)
        )
        with self.assertRaises(EtiquetaMuestraError):
            build_etiqueta_muestra(m, require_printable=True)
        with mock.patch(
            "laboratorio.services_etiqueta_muestra.send_zpl_to_network_printer"
        ) as send:
            with self.assertRaises(EtiquetaMuestraError):
                imprimir_etiqueta_muestra(m, actor=lab, view="t")
            send.assert_not_called()
