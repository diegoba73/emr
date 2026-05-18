"""Tests de política de eliminación en Django Admin para ``Paciente``."""
import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from pacientes.admin import PacienteAdmin
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestPacienteAdminDeleteBlocked:
    def setup_method(self):
        self.site = AdminSite()
        self.model_admin = PacienteAdmin(Paciente, self.site)
        self.request = RequestFactory().get("/admin/pacientes/paciente/")
        self.request.user = User.objects.create_superuser(
            username="admin.pac.delete",
            email="admin.pac.delete@example.com",
            password="x",
        )

    def test_has_delete_permission_false_sin_objeto(self):
        assert self.model_admin.has_delete_permission(self.request) is False

    def test_has_delete_permission_false_con_instancia(self):
        paciente = Paciente.objects.create(dni="ADM-DEL-0", nombre="A", apellido="B")
        assert self.model_admin.has_delete_permission(self.request, paciente) is False

    def test_delete_selected_no_esta_en_acciones(self):
        actions = self.model_admin.get_actions(self.request)
        assert "delete_selected" not in actions
