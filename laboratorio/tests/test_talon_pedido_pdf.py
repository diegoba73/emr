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

    def test_talon_dos_muestras_media_hoja_ok(self):
        """Dos tubos → PDF válido (2 medias hojas en 1 página)."""
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
