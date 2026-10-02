"""Permisos de alta/edición de médicos para operadores LIMS."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Medico

User = get_user_model()


def _user(username: str, *, rol: str, is_staff: bool = False):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
        rol=rol,
        is_staff=is_staff,
    )


@pytest.mark.django_db
class TestMedicoWritePermissions:
    def test_laboratorio_puede_crear_medico(self):
        client = APIClient()
        client.force_authenticate(user=_user("lab.med.create", rol="laboratorio"))
        response = client.post(
            "/api/medicos/",
            {
                "nombre": "Ana",
                "apellido": "Lab",
                "matricula": "MP-LAB-1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Medico.objects.filter(matricula="MP-LAB-1").exists()

    def test_bioquimico_puede_crear_medico(self):
        client = APIClient()
        client.force_authenticate(user=_user("bio.med.create", rol="bioquimico"))
        response = client.post(
            "/api/medicos/",
            {
                "nombre": "Bruno",
                "apellido": "Bio",
                "matricula": "MP-BIO-1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Medico.objects.filter(matricula="MP-BIO-1").exists()

    def test_enfermeria_no_puede_crear_medico(self):
        client = APIClient()
        client.force_authenticate(user=_user("enf.med.create", rol="enfermeria"))
        response = client.post(
            "/api/medicos/",
            {
                "nombre": "Eva",
                "apellido": "Enf",
                "matricula": "MP-ENF-1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_eliminar_medico(self):
        medico = Medico.objects.create(
            nombre="X",
            apellido="Y",
            matricula="MP-DEL-1",
        )
        client = APIClient()
        client.force_authenticate(user=_user("lab.med.del", rol="laboratorio"))
        response = client.delete(f"/api/medicos/{medico.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Medico.objects.filter(pk=medico.pk).exists()
