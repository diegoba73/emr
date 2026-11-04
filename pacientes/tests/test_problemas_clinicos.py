"""Lista de problemas clínicos + API anidada en pacientes."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.models import Paciente, ProblemaClinico
from pacientes.problemas import (
    crear_problema,
    diagnostico_vigente_snapshot,
    diagnostico_vigente_texto,
    establecer_principal_desde_texto,
)

User = get_user_model()


@pytest.mark.django_db
class TestProblemasHelpers(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:8]
        self.paciente = Paciente.objects.create(
            dni=f"DX{suf}",
            nombre="Ana",
            apellido="Dx",
            sexo="F",
        )

    def test_primer_problema_es_principal(self):
        p = crear_problema(self.paciente, texto="HTA")
        self.assertTrue(p.es_principal)
        self.assertEqual(diagnostico_vigente_texto(self.paciente.pk), "HTA")

    def test_cambiar_principal(self):
        a = crear_problema(self.paciente, texto="HTA", es_principal=True)
        b = crear_problema(self.paciente, texto="DBT2", es_principal=True)
        a.refresh_from_db()
        self.assertFalse(a.es_principal)
        self.assertTrue(b.es_principal)
        self.assertEqual(diagnostico_vigente_texto(self.paciente.pk), "DBT2")

    def test_snapshot_tuple(self):
        crear_problema(self.paciente, texto="Neumonía")
        texto, cie_id = diagnostico_vigente_snapshot(self.paciente.pk)
        self.assertEqual(texto, "Neumonía")
        self.assertIsNone(cie_id)

    def test_establecer_principal_actualiza(self):
        crear_problema(self.paciente, texto="A")
        establecer_principal_desde_texto(self.paciente, texto="B")
        self.assertEqual(diagnostico_vigente_texto(self.paciente.pk), "B")
        self.assertEqual(
            ProblemaClinico.objects.filter(
                paciente=self.paciente, estado="ACTIVO"
            ).count(),
            1,
        )


@pytest.mark.django_db
class TestProblemasApi(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:8]
        self.client = APIClient(enforce_csrf_checks=False)
        self.medico = User.objects.create_user(
            username=f"med_dx_{suf}",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.lab = User.objects.create_user(
            username=f"lab_dx_{suf}",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"AP{suf}",
            nombre="Luis",
            apellido="Api",
            sexo="M",
        )
        self.base = f"/api/pacientes/{self.paciente.pk}/problemas-clinicos"

    def test_medico_crea_y_lista(self):
        self.client.force_authenticate(self.medico)
        r = self.client.post(
            f"{self.base}/crear/",
            {"texto": "HTA esencial", "es_principal": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertTrue(r.data["es_principal"])
        r2 = self.client.get(f"{self.base}/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r2.data), 1)

    def test_lab_no_puede_crear(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            f"{self.base}/crear/",
            {"texto": "HTA"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_resolver_promueve_otro(self):
        self.client.force_authenticate(self.medico)
        a = crear_problema(self.paciente, texto="A", es_principal=True)
        b = crear_problema(self.paciente, texto="B", es_principal=False)
        r = self.client.post(f"{self.base}/{a.pk}/resolver/")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        b.refresh_from_db()
        self.assertTrue(b.es_principal)
        self.assertEqual(diagnostico_vigente_texto(self.paciente.pk), "B")
