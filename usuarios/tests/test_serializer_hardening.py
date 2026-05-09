"""Tests anti privilege-escalation de ``UserSerializer``.

Cubre los escenarios definidos por el bloque de hardening:
- staff regular NO puede crear/editar superusers, asignar ``is_staff`` ni
  ``rol='admin'``;
- superuser SÍ puede;
- usuario sin context (script/test sin request) cae en el modo seguro
  (no permite escalada).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from usuarios.serializers import UserSerializer

User = get_user_model()


def _build_serializer(actor, instance=None, **data):
    """Crea un ``UserSerializer`` con un request fake como context.

    El validador anti-escalada lee ``context['request'].user`` para decidir
    si el actor puede setear flags privilegiados.
    """
    factory = APIRequestFactory()
    request = factory.post('/dummy/', {})
    request.user = actor
    return UserSerializer(instance=instance, data=data, partial=instance is not None, context={'request': request})


@pytest.fixture
def staff_actor(db):
    return User.objects.create_user(
        username='staff_actor',
        email='staff@hard.test',
        password='Sup3rStr0ng!Pass',
        rol='secretaria',
        is_staff=True,
        is_superuser=False,
    )


@pytest.fixture
def superuser_actor(db):
    return User.objects.create_user(
        username='super_actor',
        email='super@hard.test',
        password='Sup3rStr0ng!Pass',
        rol='admin',
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
class TestUserSerializerAntiEscalation:
    """Bloqueos contra escalada en creación."""

    BASE_DATA = dict(
        username='nuevo_user_anti',
        email='nuevo@anti.test',
        password='Sup3rStr0ng!Pass',
        password_confirm='Sup3rStr0ng!Pass',
        first_name='N',
        last_name='U',
        rol='paciente',
        paciente_data={'dni': 'HARD-AE-001'},
    )

    def test_staff_no_puede_crear_superuser(self, staff_actor):
        data = {**self.BASE_DATA, 'is_superuser': True}
        s = _build_serializer(staff_actor, **data)
        assert not s.is_valid()
        assert 'is_superuser' in s.errors

    def test_staff_no_puede_crear_is_staff(self, staff_actor):
        data = {**self.BASE_DATA, 'is_staff': True}
        s = _build_serializer(staff_actor, **data)
        assert not s.is_valid()
        assert 'is_staff' in s.errors

    def test_staff_no_puede_crear_rol_admin(self, staff_actor):
        # Admin usa medico_data/paciente_data según rol; para 'admin' ninguno
        # es requerido → quitamos paciente_data.
        data = {k: v for k, v in self.BASE_DATA.items() if k != 'paciente_data'}
        data['rol'] = 'admin'
        s = _build_serializer(staff_actor, **data)
        assert not s.is_valid()
        assert 'rol' in s.errors

    def test_staff_si_puede_crear_paciente_normal(self, staff_actor):
        s = _build_serializer(staff_actor, **self.BASE_DATA)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.is_superuser is False
        assert user.is_staff is False
        assert user.rol == 'paciente'

    def test_superuser_si_puede_crear_otro_superuser(self, superuser_actor):
        data = {
            'username': 'nuevo_super',
            'email': 'nuevo_super@anti.test',
            'password': 'Sup3rStr0ng!Pass',
            'password_confirm': 'Sup3rStr0ng!Pass',
            'first_name': 'N',
            'last_name': 'S',
            'rol': 'admin',
            'is_superuser': True,
            'is_staff': True,
        }
        s = _build_serializer(superuser_actor, **data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.rol == 'admin'

    def test_sin_context_modo_seguro_bloquea_escalada(self, db):
        """Sin ``context['request']``, ningún flag privilegiado pasa."""
        data = {**self.BASE_DATA, 'is_superuser': True}
        # No usamos _build_serializer para no inyectar context.
        s = UserSerializer(data=data)
        assert not s.is_valid()
        assert 'is_superuser' in s.errors


@pytest.mark.django_db
class TestUserSerializerAntiEscalationUpdate:
    """Bloqueos contra escalada en updates."""

    @pytest.fixture
    def target_user(self, db):
        return User.objects.create_user(
            username='target_anti',
            email='target@anti.test',
            password='Sup3rStr0ng!Pass',
            rol='paciente',
            is_staff=False,
            is_superuser=False,
        )

    def test_staff_no_puede_promover_a_superuser(self, staff_actor, target_user):
        s = _build_serializer(staff_actor, instance=target_user, is_superuser=True)
        assert not s.is_valid()
        assert 'is_superuser' in s.errors

    def test_staff_no_puede_promover_a_staff(self, staff_actor, target_user):
        s = _build_serializer(staff_actor, instance=target_user, is_staff=True)
        assert not s.is_valid()
        assert 'is_staff' in s.errors

    def test_staff_no_puede_cambiar_rol_a_admin(self, staff_actor, target_user):
        s = _build_serializer(staff_actor, instance=target_user, rol='admin')
        assert not s.is_valid()
        assert 'rol' in s.errors

    def test_staff_si_puede_cambiar_rol_a_no_privilegiado(self, staff_actor, target_user):
        s = _build_serializer(staff_actor, instance=target_user, rol='enfermeria')
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.rol == 'enfermeria'
        assert user.is_staff is False
        assert user.is_superuser is False
