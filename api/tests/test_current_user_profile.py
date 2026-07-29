"""Self-service profile: GET/PUT /api/auth/current-user/."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from usuarios.models import UserProfile

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_perfil(db):
    user = User.objects.create_user(
        username='perfil_user',
        password='secret123!',
        email='antes@example.com',
        first_name='Ana',
        last_name='Perez',
        rol='secretaria',
        telefono='111',
        is_active=True,
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.ciudad = 'Trelew'
    profile.save()
    return user


@pytest.mark.django_db
class TestCurrentUserProfile:
    def test_get_incluye_profile(self, api_client, usuario_perfil):
        api_client.force_authenticate(user=usuario_perfil)
        response = api_client.get('/api/auth/current-user/')
        assert response.status_code == 200
        body = response.json()
        assert body['username'] == 'perfil_user'
        assert body['email'] == 'antes@example.com'
        assert body['profile'] is not None
        assert body['profile']['ciudad'] == 'Trelew'

    def test_put_actualiza_datos_y_profile(self, api_client, usuario_perfil):
        api_client.force_authenticate(user=usuario_perfil)
        response = api_client.put(
            '/api/auth/current-user/',
            {
                'first_name': 'Ana Maria',
                'last_name': 'Perez',
                'email': 'despues@example.com',
                'telefono': '222',
                'profile': {
                    'ciudad': 'Rawson',
                    'direccion': 'Calle 1',
                    'genero': 'F',
                    'alergias': 'Ninguna',
                },
            },
            format='json',
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body['first_name'] == 'Ana Maria'
        assert body['email'] == 'despues@example.com'
        assert body['telefono'] == '222'
        assert body['profile']['ciudad'] == 'Rawson'
        assert body['profile']['direccion'] == 'Calle 1'
        assert body['profile']['genero'] == 'F'

        usuario_perfil.refresh_from_db()
        assert usuario_perfil.email == 'despues@example.com'
        assert usuario_perfil.profile.ciudad == 'Rawson'

    def test_put_no_permite_cambiar_rol(self, api_client, usuario_perfil):
        api_client.force_authenticate(user=usuario_perfil)
        response = api_client.put(
            '/api/auth/current-user/',
            {'rol': 'admin', 'is_staff': True},
            format='json',
        )
        assert response.status_code == 200
        usuario_perfil.refresh_from_db()
        assert usuario_perfil.rol == 'secretaria'
        assert usuario_perfil.is_staff is False

    def test_cambio_password_requiere_actual(self, api_client, usuario_perfil):
        api_client.force_authenticate(user=usuario_perfil)
        bad = api_client.patch(
            '/api/auth/current-user/',
            {
                'old_password': 'wrong',
                'new_password': 'nuevasecret1',
                'new_password_confirm': 'nuevasecret1',
            },
            format='json',
        )
        assert bad.status_code == 400

        ok = api_client.patch(
            '/api/auth/current-user/',
            {
                'old_password': 'secret123!',
                'new_password': 'nuevasecret1',
                'new_password_confirm': 'nuevasecret1',
            },
            format='json',
        )
        assert ok.status_code == 200
        usuario_perfil.refresh_from_db()
        assert usuario_perfil.check_password('nuevasecret1')
