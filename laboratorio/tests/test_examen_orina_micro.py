"""Tests del examen de orina (tira + sedimento) en urocultivo."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from laboratorio.examen_orina_micro import (
    estudio_admite_examen_orina,
    normalizar_examen_orina,
)
from laboratorio.models_microbiologia import EstudioMicrobiologia, TipoCultivoMicrobiologia
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestExamenOrinaMicro(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.paciente = Paciente.objects.create(
            dni=f"D{tag}", nombre="Ana", apellido="Test"
        )
        self.cultivo_uro, _ = TipoCultivoMicrobiologia.objects.update_or_create(
            codigo="UROCULTIVO",
            defaults={"nombre": "Urocultivo", "activo": True},
        )
        self.cultivo_hemo, _ = TipoCultivoMicrobiologia.objects.update_or_create(
            codigo="HEMOCULTIVO",
            defaults={"nombre": "Hemocultivo", "activo": True},
        )
        self.estudio_uro = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            tipo_cultivo=self.cultivo_uro,
            tipo_estudio="UROCULTIVO",
            estado="RECIBIDO",
        )
        self.estudio_hemo = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            tipo_cultivo=self.cultivo_hemo,
            tipo_estudio="HEMOCULTIVO",
            estado="RECIBIDO",
        )
        self.user = User.objects.create_user(
            username=f"lab{tag}",
            email=f"lab{tag}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_admite_solo_urocultivo(self):
        self.assertTrue(estudio_admite_examen_orina(self.estudio_uro))
        self.assertFalse(estudio_admite_examen_orina(self.estudio_hemo))

    def test_normalizar_filtra_claves(self):
        data = normalizar_examen_orina({"ORI_NIT": " + ", "HACK": "x", "ORI_PH": 6})
        self.assertEqual(data["ORI_NIT"], "+")
        self.assertEqual(data["ORI_PH"], "6")
        self.assertNotIn("HACK", data)

    def test_patch_examen_orina_urocultivo(self):
        url = f"/api/lab/microbiologia/estudios/{self.estudio_uro.pk}/"
        resp = self.client.patch(
            url,
            {"examen_orina": {"ORI_NIT": "Positivo", "ORI_LEU": "10-15"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["examen_orina"]["ORI_NIT"], "Positivo")
        self.assertEqual(resp.data["examen_orina"]["ORI_LEU"], "10-15")
        self.assertTrue(resp.data["admite_examen_orina"])
        self.estudio_uro.refresh_from_db()
        self.assertEqual(self.estudio_uro.examen_orina["ORI_NIT"], "Positivo")

    def test_patch_examen_orina_rechaza_no_uro(self):
        url = f"/api/lab/microbiologia/estudios/{self.estudio_hemo.pk}/"
        resp = self.client.patch(
            url,
            {"examen_orina": {"ORI_NIT": "Positivo"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
