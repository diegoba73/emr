"""Integración del routing mínimo ``/api/usuarios/users/`` (sin ``usuarios.urls`` completo)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

FORBIDDEN_PREFIX_PATHS = (
    '/api/usuarios/register/',
    '/api/usuarios/profiles/',
    '/api/usuarios/token/',
    '/api/usuarios/token/refresh/',
    '/api/usuarios/auth/me/',
    '/api/usuarios/auth/logout/',
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_admin(api_client):
    user = User.objects.create_user(
        username='mgmt_staff',
        email='mgmt_staff@um.test',
        password='Sup3rStr0ng!Pass',
        rol='secretaria',
        is_staff=True,
        is_superuser=False,
        is_active=True,
    )
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def plain_user(api_client):
    user = User.objects.create_user(
        username='mgmt_plain',
        email='mgmt_plain@um.test',
        password='Sup3rStr0ng!Pass',
        rol='paciente',
        is_staff=False,
        is_superuser=False,
        is_active=True,
    )
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def target_paciente():
    return User.objects.create_user(
        username='mgmt_target',
        email='mgmt_target@um.test',
        password='Sup3rStr0ng!Pass',
        rol='paciente',
        is_active=True,
    )


@pytest.mark.django_db
class TestUserManagementRouting:
    def test_staff_get_users_list_200(self, api_client, staff_admin):
        response = api_client.get('/api/usuarios/users/')
        assert response.status_code == status.HTTP_200_OK, response.data

    def test_non_staff_get_users_forbidden(self, api_client, plain_user):
        response = api_client.get('/api/usuarios/users/')
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ), response.data

    def test_delete_returns_405_user_persists(self, api_client, staff_admin, target_paciente):
        uid = target_paciente.id
        response = api_client.delete(f'/api/usuarios/users/{uid}/')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert User.objects.filter(pk=uid).exists()

    def test_activate_deactivate(self, api_client, staff_admin, target_paciente):
        target_paciente.is_active = False
        target_paciente.save(update_fields=['is_active'])

        r_act = api_client.post(f'/api/usuarios/users/{target_paciente.pk}/activate/')
        assert r_act.status_code == status.HTTP_200_OK, getattr(r_act, 'data', r_act)

        target_paciente.refresh_from_db()
        assert target_paciente.is_active is True

        r_deact = api_client.post(f'/api/usuarios/users/{target_paciente.pk}/deactivate/')
        assert r_deact.status_code == status.HTTP_200_OK, getattr(r_deact, 'data', r_deact)

        target_paciente.refresh_from_db()
        assert target_paciente.is_active is False

    @pytest.mark.parametrize('path', FORBIDDEN_PREFIX_PATHS)
    def test_non_user_management_paths_not_200(self, api_client, path):
        """Rutas no montadas: no deben responder 200 (preferencia 404)."""
        response = api_client.get(path)
        assert response.status_code != status.HTTP_200_OK
        assert response.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ), f'{path} -> {response.status_code}'
