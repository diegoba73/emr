"""Permisos de alta de médicos: lab/bio pueden crear; enfermería/paciente no."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Medico

User = get_user_model()


@pytest.mark.django_db
class TestMedicoEscrituraPermisosAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.client = APIClient()

    def _post_medico(self, user, matricula_suffix: str):
        self.client.force_authenticate(user=user)
        return self.client.post(
            "/api/medicos/",
            {
                "nombre": "Nuevo",
                "apellido": "Lab",
                "matricula": f"MX{matricula_suffix}",
            },
            format="json",
        )

    def test_laboratorio_puede_crear_medico(self):
        lab = User.objects.create_user(
            username=f"lab_med_{self.suf}",
            password="x",
            rol="laboratorio",
        )
        r = self._post_medico(lab, f"L{self.suf}")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertTrue(Medico.objects.filter(matricula=f"MXL{self.suf}").exists())

    def test_bioquimico_puede_crear_medico(self):
        bio = User.objects.create_user(
            username=f"bio_med_{self.suf}",
            password="x",
            rol="bioquimico",
        )
        r = self._post_medico(bio, f"B{self.suf}")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertTrue(Medico.objects.filter(matricula=f"MXB{self.suf}").exists())

    def test_enfermeria_no_puede_crear_medico(self):
        enf = User.objects.create_user(
            username=f"enf_med_{self.suf}",
            password="x",
            rol="enfermeria",
        )
        r = self._post_medico(enf, f"E{self.suf}")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_no_puede_crear_medico(self):
        pac = User.objects.create_user(
            username=f"pac_med_{self.suf}",
            password="x",
            rol="paciente",
        )
        r = self._post_medico(pac, f"P{self.suf}")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
