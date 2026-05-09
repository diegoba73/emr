"""Tests mínimos del rol ``laboratorio``: modelo, serializers y JWT.

No cubre permisos LIMS ni ViewSets de laboratorio. El test de JWT no
depende del montaje global de ``usuarios.urls`` (deliberadamente fuera de
``synesis/urls.py`` por hardening pendiente): usa ``APIRequestFactory``
contra ``CustomTokenObtainPairView`` directamente.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory

from usuarios.serializers import UserSerializer
from usuarios.views import CustomTokenObtainPairView

User = get_user_model()


@pytest.mark.django_db
class TestLaboratorioRoleModel:
    def test_usuario_con_rol_laboratorio_y_display(self):
        u = User.objects.create_user(
            username='lab_model_user',
            email='lab-model@example.com',
            password='secret123!',
            rol='laboratorio',
        )
        u.full_clean()
        assert u.rol == 'laboratorio'
        assert u.get_rol_display() == 'Laboratorio'
        assert u.es_medico is False
        assert u.es_enfermeria is False


@pytest.mark.django_db
class TestLaboratorioRoleSerializers:
    def test_user_serializer_acepta_rol_laboratorio(self):
        data = {
            'username': 'lab_admin_created',
            'email': 'lab-admin-created@example.com',
            'password': 'StrongP@ssw0rd!',
            'password_confirm': 'StrongP@ssw0rd!',
            'rol': 'laboratorio',
            'first_name': 'Lee',
            'last_name': 'Ab',
            'is_active': True,
        }
        serializer = UserSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.rol == 'laboratorio'


@pytest.mark.django_db
class TestLaboratorioRoleAuthEndpoints:
    @pytest.fixture
    def client(self):
        return APIClient(enforce_csrf_checks=False)

    @pytest.fixture
    def usuario_laboratorio(self):
        return User.objects.create_user(
            username='lab_auth_user',
            email='lab-auth@example.com',
            password='secret123!',
            rol='laboratorio',
            is_active=True,
        )

    def test_login_y_current_user_session(self, client, usuario_laboratorio):
        r_login = client.post(
            '/api/auth/login/',
            {'username': 'lab_auth_user', 'password': 'secret123!'},
            format='json',
        )
        assert r_login.status_code == 200
        body = r_login.json()
        assert body['user']['rol'] == 'LABORATORIO'

        r_me = client.get('/api/auth/current-user/')
        assert r_me.status_code == 200
        assert r_me.json()['rol'] == 'laboratorio'

    def test_jwt_token_incluye_rol_laboratorio(self, usuario_laboratorio):
        """Verifica el payload JWT sin depender de ``/api/usuarios/token/``.

        ``usuarios.urls`` no está montado en ``synesis/urls.py`` (decisión
        deliberada hasta cerrar el bloque de hardening). Para no acoplar el
        test al routing global, invocamos la vista directamente con
        ``APIRequestFactory``.
        """
        factory = APIRequestFactory()
        view = CustomTokenObtainPairView.as_view()
        request = factory.post(
            '/token/',
            {'username': 'lab_auth_user', 'password': 'secret123!'},
            format='json',
        )
        response = view(request)
        response.render()
        assert response.status_code == 200, response.data
        payload = response.data
        assert 'access' in payload
        assert 'refresh' in payload
        assert payload['user']['rol'] == 'laboratorio'
