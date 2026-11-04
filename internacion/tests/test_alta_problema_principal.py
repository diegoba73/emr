"""Al alta de internación sincroniza el problema clínico principal."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from internacion.models import Cama, Internacion, Sector
from pacientes.models import Paciente
from pacientes.problemas import diagnostico_vigente_texto

User = get_user_model()


@pytest.mark.django_db
class TestAltaProblemaPrincipal(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:8]
        self.client = APIClient(enforce_csrf_checks=False)
        self.medico = User.objects.create_user(
            username=f"med_alta_{suf}",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"AL{suf}",
            nombre="Alta",
            apellido="Dx",
            sexo="F",
        )
        sector = Sector.objects.create(nombre=f"S{suf}", activo=True)
        self.cama = Cama.objects.create(
            nombre=f"C{suf}", sector=sector, estado="DISPONIBLE", activo=True
        )
        self.internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=self.cama,
            activo=True,
            diagnostico_ingreso="Neumonía ingreso",
        )

    def test_alta_con_egreso_actualiza_principal(self):
        self.client.force_authenticate(self.medico)
        r = self.client.post(
            f"/api/internacion/internaciones/{self.internacion.pk}/alta/",
            {"diagnostico_egreso": "Neumonía resuelta / HTA"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertEqual(
            diagnostico_vigente_texto(self.paciente.pk),
            "Neumonía resuelta / HTA",
        )
        self.internacion.refresh_from_db()
        self.assertFalse(self.internacion.activo)
        self.assertEqual(self.internacion.diagnostico_egreso, "Neumonía resuelta / HTA")
