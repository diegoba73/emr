"""Tests del hardening en ViewSets de ``usuarios``.

Cubre, sin depender del routing global de ``usuarios.urls``:
- ``UserViewSet.bulk_activate``/``bulk_deactivate`` respetan ``get_queryset``
  (un staff regular no puede tocar superusers);
- ``UserViewSet.destroy`` devuelve 405 (sin borrado físico de User);
- ``activate``/``deactivate`` siguen operativos;
- ``UserProfileViewSet.destroy`` devuelve 405;
- usuario común solo ve su propio perfil;
- password no aparece en respuestas (``UserListSerializer`` /
  ``UserDetailSerializer``);
- registro público fuerza ``rol='paciente'`` aunque el cliente envíe otro
  rol o flags privilegiados (campos no existen en el serializer).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from usuarios.serializers import (
    PacienteRegistrationSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from usuarios.views import (
    PacienteRegisterView,
    UserProfileViewSet,
    UserViewSet,
)
from usuarios.models import UserProfile

User = get_user_model()


# ---------------------------------------------------------------------------
# UserViewSet — bulk respeta get_queryset
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUserViewSetBulkRespectsQueryset:
    @pytest.fixture
    def staff_actor(self):
        return User.objects.create_user(
            username='hard_bulk_staff',
            email='hard_bulk_staff@hd.test',
            password='Sup3rStr0ng!Pass',
            rol='secretaria',
            is_staff=True,
            is_superuser=False,
        )

    @pytest.fixture
    def superuser_objetivo(self):
        return User.objects.create_user(
            username='hard_bulk_super',
            email='hard_bulk_super@hd.test',
            password='Sup3rStr0ng!Pass',
            rol='admin',
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

    @pytest.fixture
    def paciente_objetivo(self):
        return User.objects.create_user(
            username='hard_bulk_pac',
            email='hard_bulk_pac@hd.test',
            password='Sup3rStr0ng!Pass',
            rol='paciente',
            is_active=True,
        )

    def _post_bulk(self, action_name, actor, user_ids):
        factory = APIRequestFactory()
        request = factory.post('/dummy/', {'user_ids': user_ids}, format='json')
        force_authenticate(request, user=actor)
        view = UserViewSet.as_view({'post': action_name})
        return view(request)

    def test_bulk_deactivate_no_alcanza_superuser(self, staff_actor, superuser_objetivo, paciente_objetivo):
        response = self._post_bulk(
            'bulk_deactivate',
            staff_actor,
            [superuser_objetivo.id, paciente_objetivo.id],
        )
        assert response.status_code == 200, response.data
        # Solo el paciente entró al filtro de get_queryset (staff no ve superusers).
        assert response.data['affected'] == 1
        superuser_objetivo.refresh_from_db()
        paciente_objetivo.refresh_from_db()
        assert superuser_objetivo.is_active is True  # intacto
        assert paciente_objetivo.is_active is False  # afectado

    def test_bulk_activate_no_alcanza_superuser(self, staff_actor, superuser_objetivo, paciente_objetivo):
        # Primero desactivamos al paciente para que bulk_activate haga algo.
        paciente_objetivo.is_active = False
        paciente_objetivo.save(update_fields=['is_active'])
        # Y desactivamos al superuser para "intentar" reactivarlo desde staff.
        superuser_objetivo.is_active = False
        superuser_objetivo.save(update_fields=['is_active'])

        response = self._post_bulk(
            'bulk_activate',
            staff_actor,
            [superuser_objetivo.id, paciente_objetivo.id],
        )
        assert response.status_code == 200, response.data
        assert response.data['affected'] == 1
        superuser_objetivo.refresh_from_db()
        paciente_objetivo.refresh_from_db()
        assert superuser_objetivo.is_active is False  # intacto (no visible)
        assert paciente_objetivo.is_active is True  # afectado


# ---------------------------------------------------------------------------
# UserViewSet — DELETE bloqueado; activate/deactivate intactos
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUserViewSetDestroyHardening:
    @pytest.fixture
    def staff_actor(self):
        return User.objects.create_user(
            username='hard_del_staff',
            email='hard_del_staff@hd.test',
            password='Sup3rStr0ng!Pass',
            rol='secretaria',
            is_staff=True,
            is_superuser=False,
        )

    @pytest.fixture
    def target_user(self):
        return User.objects.create_user(
            username='hard_del_target',
            email='hard_del_target@hd.test',
            password='Sup3rStr0ng!Pass',
            rol='paciente',
            is_active=True,
        )

    def test_destroy_devuelve_405_conserva_usuario_y_is_active(self, staff_actor, target_user):
        uid = target_user.id
        is_active_before = target_user.is_active
        factory = APIRequestFactory()
        request = factory.delete(f'/dummy/{uid}/')
        force_authenticate(request, user=staff_actor)
        view = UserViewSet.as_view({'delete': 'destroy'})
        response = view(request, pk=uid)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert User.objects.filter(pk=uid).exists()
        target_user.refresh_from_db()
        assert target_user.is_active == is_active_before

    def test_activate_sigue_funcionando(self, staff_actor, target_user):
        target_user.is_active = False
        target_user.save(update_fields=['is_active'])
        factory = APIRequestFactory()
        request = factory.post(f'/dummy/{target_user.pk}/activate/')
        force_authenticate(request, user=staff_actor)
        view = UserViewSet.as_view({'post': 'activate'})
        response = view(request, pk=target_user.pk)
        assert response.status_code == status.HTTP_200_OK, getattr(response, 'data', response)
        target_user.refresh_from_db()
        assert target_user.is_active is True

    def test_deactivate_sigue_funcionando(self, staff_actor, target_user):
        assert target_user.is_active is True
        factory = APIRequestFactory()
        request = factory.post(f'/dummy/{target_user.pk}/deactivate/')
        force_authenticate(request, user=staff_actor)
        view = UserViewSet.as_view({'post': 'deactivate'})
        response = view(request, pk=target_user.pk)
        assert response.status_code == status.HTTP_200_OK, getattr(response, 'data', response)
        target_user.refresh_from_db()
        assert target_user.is_active is False


# ---------------------------------------------------------------------------
# UserProfileViewSet — destroy bloqueado
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUserProfileViewSetHardening:
    def _make_user(self, **kwargs):
        defaults = dict(
            username=kwargs.pop('username', 'prof_test'),
            email=kwargs.pop('email', 'prof_test@hd.test'),
            password='Sup3rStr0ng!Pass',
            rol=kwargs.pop('rol', 'paciente'),
        )
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)

    def test_destroy_devuelve_405_y_conserva_perfil(self):
        owner = self._make_user(username='hard_prof_owner', email='hard_prof_owner@hd.test')
        # signal crea perfil automáticamente
        profile = owner.profile
        assert profile is not None

        factory = APIRequestFactory()
        request = factory.delete(f'/dummy/{profile.pk}/')
        force_authenticate(request, user=owner)
        view = UserProfileViewSet.as_view({'delete': 'destroy'})
        response = view(request, pk=profile.pk)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert UserProfile.objects.filter(pk=profile.pk).exists()

    def test_usuario_comun_solo_ve_su_propio_perfil(self):
        owner = self._make_user(username='hard_prof_own2', email='hard_prof_own2@hd.test')
        ajeno = self._make_user(username='hard_prof_other', email='hard_prof_other@hd.test')
        # Ambos tienen perfil por signal.
        assert UserProfile.objects.filter(user=ajeno).exists()

        factory = APIRequestFactory()
        request = factory.get('/dummy/')
        force_authenticate(request, user=owner)
        view = UserProfileViewSet.as_view({'get': 'list'})
        response = view(request)
        assert response.status_code == 200, response.data
        rows = response.data['results'] if 'results' in response.data else response.data
        ids = {row['user'] for row in rows}
        assert owner.id in ids
        assert ajeno.id not in ids


# ---------------------------------------------------------------------------
# Serializers no exponen password ni tokens
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestSerializersDoNotLeakPassword:
    def test_user_list_serializer_no_password(self):
        u = User.objects.create_user(
            username='leak_list',
            email='leak_list@hd.test',
            password='Sup3rStr0ng!Pass',
        )
        data = UserListSerializer(u).data
        assert 'password' not in data
        assert 'password_confirm' not in data

    def test_user_detail_serializer_no_password(self):
        u = User.objects.create_user(
            username='leak_detail',
            email='leak_detail@hd.test',
            password='Sup3rStr0ng!Pass',
        )
        data = UserDetailSerializer(u).data
        assert 'password' not in data
        assert 'password_confirm' not in data


# ---------------------------------------------------------------------------
# Registro público — rol forzado y campos privilegiados ignorados
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestPacienteRegisterPublic:
    def test_serializer_no_acepta_campo_rol(self):
        """Si el cliente envía ``rol``, el serializer lo ignora silenciosamente."""
        data = {
            'email': 'reg_public@hd.test',
            'password': 'Sup3rStr0ng!Pass',
            'nombre': 'N',
            'apellido': 'A',
            'dni': 'HARD-PUB-001',
            'telefono': '111',
            'fecha_nacimiento': '1990-01-01',
            # Intentos de escalada — no están en fields, deben ser ignorados:
            'rol': 'admin',
            'is_superuser': True,
            'is_staff': True,
        }
        s = PacienteRegistrationSerializer(data=data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.rol == 'paciente'
        assert user.is_superuser is False
        assert user.is_staff is False

    def test_view_devuelve_201_y_user_id_solo(self):
        factory = APIRequestFactory()
        request = factory.post(
            '/dummy/',
            {
                'email': 'reg_public_view@hd.test',
                'password': 'Sup3rStr0ng!Pass',
                'nombre': 'N',
                'apellido': 'A',
                'dni': 'HARD-PUB-002',
                'telefono': '111',
                'fecha_nacimiento': '1990-01-01',
            },
            format='json',
        )
        view = PacienteRegisterView.as_view()
        response = view(request)
        response.render()
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert 'user_id' in response.data
        # No debe filtrar email completo en la respuesta (response.data lo limita
        # a ``user_id`` y ``message``); password jamás.
        assert 'password' not in response.data
        assert 'email' not in response.data
