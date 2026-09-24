"""
Tests: etiqueta ZPL 40×23 mm para EstudioMicrobiologia (mismo perfil que lab clínico).
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models_microbiologia import (
    EstudioMicrobiologia,
    TipoCultivoMicrobiologia,
    TipoMuestraMicrobiologia,
)
from laboratorio.services_etiqueta_microbiologia import (
    build_etiqueta_estudio_micro,
    tipo_operacional_imprimible_micro,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestEtiquetaZplMicrobiologia(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_ezm_{suf}",
            email=f"lab-ezm-{suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_ezm_{suf}",
            email=f"med-ezm-{suf}@t.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"7{suf[:7]}", nombre="Ana", apellido="Lopez"
        )
        esp = Especialidad.objects.create(nombre=f"EspEZM {suf}")
        self.medico = Medico.objects.create(
            nombre="Bob", apellido="Diaz", matricula=f"EZ-{suf}", especialidad=esp
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
            origen_solicitud="GUARDIA",
            tipo_cultivo=cultivo,
            tipo_muestra_micro=tm,
            tipo_estudio=cultivo.codigo,
            estado="PENDIENTE",
        )

    def test_tipo_operacional_es_codigo_cultivo(self):
        self.assertEqual(tipo_operacional_imprimible_micro(self.estudio), "UROCULTIVO")

    def test_preview_zpl_sin_mutar_etiquetas(self):
        self.assertIsNone(self.estudio.etiquetas_impresas_at)
        self.client.force_authenticate(self.lab)
        r = self.client.get(
            f"/api/lab/microbiologia/estudios/{self.estudio.pk}/etiqueta-zpl/"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        body = r.json()
        self.assertEqual(body["estudio_id"], self.estudio.pk)
        self.assertTrue(body["printable"], body.get("validation_errors"))
        self.assertEqual(len(body["lines"]), 4)
        self.assertEqual(body["lines"][0], self.estudio.numero)
        self.assertIn("LOPEZ", body["lines"][1])
        self.assertIn("^PW320", body["zpl"])
        self.estudio.refresh_from_db()
        self.assertIsNone(self.estudio.etiquetas_impresas_at)
        self.assertIsNone(self.estudio.codigo_barra)

    def test_imprimir_y_confirmar_zpl(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/microbiologia/estudios/{self.estudio.pk}/imprimir-etiqueta/",
                {},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        body = r.json()
        self.assertEqual(body["resultado"], "prepared")
        self.assertTrue(body["zpl"].strip().startswith("^XA"))
        self.estudio.refresh_from_db()
        self.assertIsNotNone(self.estudio.etiquetas_impresas_at)
        self.assertEqual(self.estudio.codigo_barra, self.estudio.numero)
        self.assertEqual(self.estudio.estado, "PENDIENTE")

        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/microbiologia/estudios/{self.estudio.pk}/imprimir-etiqueta/confirmar/",
                {"profile": body["profile"]},
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                metadata__accion="micro_etiqueta_print",
                metadata__estudio_id=self.estudio.pk,
                metadata__transport="local_agent",
            ).exists()
        )

    def test_medico_403_en_zpl(self):
        self.client.force_authenticate(self.med)
        r = self.client.get(
            f"/api/lab/microbiologia/estudios/{self.estudio.pk}/etiqueta-zpl/"
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_build_service_cuatro_lineas(self):
        payload = build_etiqueta_estudio_micro(self.estudio, require_printable=False)
        self.assertTrue(payload.printable, payload.validation_errors)
        self.assertEqual(len(payload.lines), 4)
        self.assertIn("UROCULTIVO", payload.lines[3])
