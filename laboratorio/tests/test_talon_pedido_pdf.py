"""Talón PDF de respaldo — clínica y microbiología (sin mutar FSM)."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.muestra_estado import crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestTalonPedidoClinicoApi(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_tal_{suf}",
            email=f"lab-tal-{suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_tal_{suf}",
            email=f"med-tal-{suf}@t.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"7{suf[:7]}", nombre="Juan", apellido="Pérez"
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.medico = Medico.objects.create(
            nombre="Ana", apellido="García", matricula=f"M-{suf}", especialidad=esp
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TM{suf}", nombre="Sangre", activo=True
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        self.sol.tipos_examen.add(self.te)
        ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te, valor_obtenido=""
        )

    def test_talon_pdf_200_sin_mutar_estado(self):
        crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=self.lab,
            view="t",
        )
        self.sol.refresh_from_db()
        estado_antes = self.sol.estado
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(f"/api/lab/solicitudes/{self.sol.pk}/talon-pdf/")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertIn("talon-orden-", r.get("Content-Disposition", ""))
        self.sol.refresh_from_db()
        self.assertEqual(self.sol.estado, estado_antes)
        self.assertTrue(
            AuditEvent.objects.filter(
                metadata__accion="talon_pedido_pdf_download",
                metadata__solicitud_id=self.sol.pk,
            ).exists()
        )

    def test_talon_una_muestra_sin_copia_ni_borde_punteado(self):
        """Un tubo → una página por orden, sin línea de corte."""
        from laboratorio.talon_pedido_pdf import generar_talon_solicitud_pdf_bytes

        crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=self.lab,
            view="t",
        )
        pdf = generar_talon_solicitud_pdf_bytes(self.sol)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertNotIn(b"cortar", pdf)
        pages = pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")
        self.assertEqual(pages, 1)

    def test_talon_dos_muestras_una_pagina_por_orden(self):
        """Dos tubos → 1 página (un talón por orden, no por tubo)."""
        from laboratorio.talon_pedido_pdf import generar_talon_solicitud_pdf_bytes

        crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=self.lab,
            view="t",
        )
        crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=self.lab,
            view="t",
        )
        pdf = generar_talon_solicitud_pdf_bytes(self.sol)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)
        self.assertNotIn(b"cortar", pdf)
        pages = pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")
        self.assertEqual(pages, 1)

    def test_talon_lista_todos_examenes_sin_truncar(self):
        """Con muchos exámenes no aparece “y N más”; se listan todos."""
        from laboratorio.talon_pedido_pdf import (
            _examenes_solicitud,
            columnas_examenes,
            generar_talon_solicitud_pdf_bytes,
        )

        nombres = []
        for i in range(20):
            te = TipoExamen.objects.create(
                codigo=f"EX{i}_{self.te.codigo[-4:]}",
                nombre=f"Examen Extra {i:02d}",
                tipo_muestra_requerida=self.tm,
                precio=1,
                activo=True,
            )
            self.sol.tipos_examen.add(te)
            ResultadoExamen.objects.create(
                solicitud=self.sol, tipo_examen=te, valor_obtenido=""
            )
            nombres.append(te.nombre)

        listado = _examenes_solicitud(self.sol)
        for n in nombres:
            self.assertIn(n, listado)
        self.assertIn("Glucosa", listado)
        self.assertGreaterEqual(len(listado), 21)

        cols = columnas_examenes(listado)
        self.assertEqual(len(cols), 2)
        self.assertEqual(len(cols[0]), 15)
        self.assertEqual(len(cols[1]), len(listado) - 15)

        pdf = generar_talon_solicitud_pdf_bytes(self.sol)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertNotRegex(pdf.decode("latin-1", errors="ignore"), r"y \d+ m.s")
        # ReportLab escribe literales; al menos los nombres cortos deben aparecer.
        self.assertIn(b"Examen Extra 00", pdf)
        self.assertIn(b"Examen Extra 19", pdf)

    def test_columnas_examenes_max_15(self):
        from laboratorio.talon_pedido_pdf import columnas_examenes

        self.assertEqual(columnas_examenes([f"e{i}" for i in range(15)]), [[f"e{i}" for i in range(15)]])
        cols = columnas_examenes([f"e{i}" for i in range(16)])
        self.assertEqual(len(cols), 2)
        self.assertEqual(len(cols[0]), 15)
        self.assertEqual(cols[1], ["e15"])
        cols3 = columnas_examenes([f"e{i}" for i in range(45)])
        self.assertEqual(len(cols3), 3)
        self.assertTrue(all(len(c) == 15 for c in cols3))

    def test_talon_panel_sin_expandir_componentes(self):
        """Un perfil se muestra como ítem; no lista cada examen del panel."""
        from laboratorio.models import PanelExamen
        from laboratorio.talon_pedido_pdf import _examenes_solicitud

        te_a = TipoExamen.objects.create(
            codigo=f"HA_{self.te.codigo[-4:]}",
            nombre="Hematies Panel",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        te_b = TipoExamen.objects.create(
            codigo=f"HB_{self.te.codigo[-4:]}",
            nombre="Hemoglobina Panel",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        panel = PanelExamen.objects.create(
            codigo=f"PAN_HEMO_{self.te.codigo[-4:]}",
            nombre="Hemograma Completo",
            activo=True,
        )
        panel.tipos_examen.add(te_a, te_b)
        self.sol.paneles.add(panel)
        self.sol.tipos_examen.add(te_a, te_b)
        ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=te_a, valor_obtenido=""
        )
        ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=te_b, valor_obtenido=""
        )

        listado = _examenes_solicitud(self.sol)
        self.assertIn("Hemograma Completo", listado)
        self.assertNotIn("Hematies Panel", listado)
        self.assertNotIn("Hemoglobina Panel", listado)
        self.assertIn("Glucosa", listado)

    def test_talon_pdf_medico_403(self):
        self.client.force_authenticate(self.med)
        r = self.client.get(f"/api/lab/solicitudes/{self.sol.pk}/talon-pdf/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class TestTalonPedidoMicroApi(TestCase):
    def setUp(self):
        from laboratorio.models_microbiologia import (
            EstudioMicrobiologia,
            TipoCultivoMicrobiologia,
            TipoMuestraMicrobiologia,
        )

        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_mt_{suf}",
            email=f"lab-mt-{suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_mt_{suf}",
            email=f"med-mt-{suf}@t.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"8{suf[:7]}", nombre="Luis", apellido="Sosa"
        )
        esp = Especialidad.objects.create(nombre=f"EspM {suf}")
        self.medico = Medico.objects.create(
            nombre="Eva", apellido="Ruiz", matricula=f"MM-{suf}", especialidad=esp
        )
        cultivo, _ = TipoCultivoMicrobiologia.objects.get_or_create(
            codigo="UROCULTIVO",
            defaults={"nombre": "Urocultivo", "activo": True},
        )
        if not cultivo.activo:
            cultivo.activo = True
            cultivo.save(update_fields=["activo"])
        tm, _ = TipoMuestraMicrobiologia.objects.get_or_create(
            codigo=f"ORINA_{suf}",
            defaults={"nombre": "Orina", "activo": True},
        )
        self.estudio = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            tipo_cultivo=cultivo,
            tipo_muestra_micro=tm,
            tipo_estudio=cultivo.codigo,
            estado="PENDIENTE",
        )

    def test_talon_micro_sin_mutar_etiquetas_ni_estado(self):
        self.assertIsNone(self.estudio.etiquetas_impresas_at)
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(
                f"/api/lab/microbiologia/estudios/{self.estudio.pk}/talon-pdf/"
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.estudio.refresh_from_db()
        self.assertEqual(self.estudio.estado, "PENDIENTE")
        self.assertIsNone(self.estudio.etiquetas_impresas_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                metadata__accion="talon_pedido_pdf_download",
                metadata__estudio_id=self.estudio.pk,
            ).exists()
        )

    def test_talon_micro_medico_403(self):
        self.client.force_authenticate(self.med)
        r = self.client.get(
            f"/api/lab/microbiologia/estudios/{self.estudio.pk}/talon-pdf/"
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
