"""Tests de trazabilidad estructural ``creado_por`` / ``modificado_por`` en Paciente."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.admin import PacienteAdmin
from pacientes.models import Paciente

User = get_user_model()


def _payload_create(**overrides):
    base = {
        "dni": "PROV-BASE-0",
        "nombre": "Juan",
        "apellido": "Pérez",
        "fecha_nacimiento": "1990-05-15",
    }
    base.update(overrides)
    return base


def _admin(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
        rol="admin",
        is_staff=True,
    )


@pytest.mark.django_db
class TestPacienteProvenanceModel:
    def test_objects_create_permite_null_en_provenance(self):
        paciente = Paciente.objects.create(
            dni="PROV-NULL-0",
            nombre="Legacy",
            apellido="SinActor",
        )
        assert paciente.creado_por_id is None
        assert paciente.modificado_por_id is None


@pytest.mark.django_db
class TestPacienteProvenanceAPI:
    def test_get_legacy_con_provenance_null_200(self):
        paciente = Paciente.objects.create(
            dni="PROV-GET-0",
            nombre="Legacy",
            apellido="Get",
        )
        client = APIClient()
        client.force_authenticate(user=_admin("admin.prov.get"))
        response = client.get(f"/api/pacientes/{paciente.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["creado_por"] is None
        assert response.data["modificado_por"] is None

    def test_post_setea_creado_y_modificado_por(self):
        admin = _admin("admin.prov.create")
        client = APIClient()
        client.force_authenticate(user=admin)
        data = _payload_create(dni="PROV-CRT-0")
        response = client.post("/api/pacientes/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        paciente = Paciente.objects.get(pk=response.data["id"])
        assert paciente.creado_por_id == admin.id
        assert paciente.modificado_por_id == admin.id
        assert response.data["creado_por"] == admin.username
        assert response.data["modificado_por"] == admin.username

    def test_patch_actualiza_solo_modificado_por(self):
        creator = _admin("admin.prov.creator")
        editor = _admin("admin.prov.editor")
        paciente = Paciente.objects.create(
            dni="PROV-PATCH-0",
            nombre="Antes",
            apellido="Patch",
            fecha_nacimiento=date(1991, 2, 2),
            creado_por=creator,
            modificado_por=creator,
        )
        client = APIClient()
        client.force_authenticate(user=editor)
        response = client.patch(
            f"/api/pacientes/{paciente.id}/",
            {"telefono": "555"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        paciente.refresh_from_db()
        assert paciente.creado_por_id == creator.id
        assert paciente.modificado_por_id == editor.id
        assert response.data["creado_por"] == creator.username
        assert response.data["modificado_por"] == editor.username

    def test_put_actualiza_solo_modificado_por(self):
        creator = _admin("admin.prov.put.creator")
        editor = _admin("admin.prov.put.editor")
        paciente = Paciente.objects.create(
            dni="PROV-PUT-0",
            nombre="Put",
            apellido="Test",
            fecha_nacimiento=date(1992, 3, 3),
            creado_por=creator,
            modificado_por=creator,
        )
        client = APIClient()
        client.force_authenticate(user=editor)
        payload = _payload_create(dni="PROV-PUT-0", telefono="999")
        response = client.put(
            f"/api/pacientes/{paciente.id}/",
            payload,
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        paciente.refresh_from_db()
        assert paciente.creado_por_id == creator.id
        assert paciente.modificado_por_id == editor.id

    def test_cliente_no_puede_suplantar_actor_en_post(self):
        admin = _admin("admin.prov.ro.post")
        impostor = _admin("admin.prov.impostor")
        client = APIClient()
        client.force_authenticate(user=admin)
        data = _payload_create(
            dni="PROV-RO-POST-0",
            creado_por=impostor.username,
            modificado_por=impostor.username,
        )
        response = client.post("/api/pacientes/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        paciente = Paciente.objects.get(pk=response.data["id"])
        assert paciente.creado_por_id == admin.id
        assert paciente.modificado_por_id == admin.id

    def test_cliente_no_puede_suplantar_actor_en_patch(self):
        creator = _admin("admin.prov.ro.patch.creator")
        editor = _admin("admin.prov.ro.patch.editor")
        impostor = _admin("admin.prov.ro.patch.impostor")
        paciente = Paciente.objects.create(
            dni="PROV-RO-PATCH-0",
            nombre="Ro",
            apellido="Patch",
            creado_por=creator,
            modificado_por=creator,
        )
        client = APIClient()
        client.force_authenticate(user=editor)
        response = client.patch(
            f"/api/pacientes/{paciente.id}/",
            {
                "telefono": "111",
                "creado_por": impostor.username,
                "modificado_por": impostor.username,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        paciente.refresh_from_db()
        assert paciente.creado_por_id == creator.id
        assert paciente.modificado_por_id == editor.id


@pytest.mark.django_db
class TestPacienteProvenanceAdmin:
    def test_provenance_fields_readonly(self):
        readonly = PacienteAdmin(Paciente, None).readonly_fields
        assert "creado_por" in readonly
        assert "modificado_por" in readonly

    def test_delete_sigue_bloqueado(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        site = AdminSite()
        model_admin = PacienteAdmin(Paciente, site)
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            username="admin.prov.del",
            email="admin.prov.del@example.com",
            password="x",
        )
        assert model_admin.has_delete_permission(request) is False
        assert "delete_selected" not in model_admin.get_actions(request)
