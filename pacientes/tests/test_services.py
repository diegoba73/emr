"""Tests para ``pacientes.services.ensure_paciente_linked_to_user``.

El servicio es prerrequisito para ``turnos`` (ver ``turnos/views.py``). Debe:

- Devolver ``None`` para usuarios cuyo rol no es ``paciente``.
- Devolver ``user.paciente`` si la relación ya existe.
- Vincular por email único cuando el ``Paciente`` está sin usuario.
- Vincular por ``dni == username`` cuando el username es solo dígitos.
- No reasignar fichas ya vinculadas a otro usuario.
- No crear pacientes automáticamente.
"""
import pytest
from django.contrib.auth import get_user_model

from pacientes.models import Paciente
from pacientes.services import ensure_paciente_linked_to_user

User = get_user_model()


@pytest.fixture
def user_paciente(db):
    user = User.objects.create_user(
        username="paciente.svc.alpha",
        email="alpha.svc@example.com",
        password="x",
        rol="paciente",
    )
    return user


@pytest.mark.django_db
class TestEnsurePacienteLinkedToUser:
    def test_rol_no_paciente_devuelve_none(self):
        user = User.objects.create_user(
            username="medico.svc.alpha",
            email="medico.svc@example.com",
            password="x",
            rol="medico",
        )
        assert ensure_paciente_linked_to_user(user) is None

    def test_paciente_ya_vinculado_devuelve_existente(self, user_paciente):
        paciente = Paciente.objects.create(
            dni="SVC-LINK-0", nombre="Juan", apellido="Pérez", user=user_paciente
        )
        result = ensure_paciente_linked_to_user(user_paciente)
        assert result is not None
        assert result.pk == paciente.pk

    def test_vincula_por_email_unico(self, user_paciente):
        paciente = Paciente.objects.create(
            dni="SVC-LINK-1",
            nombre="Ana",
            apellido="López",
            email=user_paciente.email,
        )
        result = ensure_paciente_linked_to_user(user_paciente)
        assert result is not None
        assert result.pk == paciente.pk
        paciente.refresh_from_db()
        assert paciente.user_id == user_paciente.id

    def test_no_vincula_si_email_ambiguo(self, user_paciente):
        Paciente.objects.create(
            dni="SVC-LINK-2A", nombre="A", apellido="X", email=user_paciente.email
        )
        Paciente.objects.create(
            dni="SVC-LINK-2B", nombre="B", apellido="Y", email=user_paciente.email
        )
        assert ensure_paciente_linked_to_user(user_paciente) is None

    def test_vincula_por_dni_igual_a_username(self, db):
        user = User.objects.create_user(
            username="32145678",
            email="dnis@example.com",
            password="x",
            rol="paciente",
        )
        paciente = Paciente.objects.create(
            dni="32145678", nombre="Carlos", apellido="DNI"
        )
        result = ensure_paciente_linked_to_user(user)
        assert result is not None
        assert result.pk == paciente.pk
        paciente.refresh_from_db()
        assert paciente.user_id == user.id

    def test_no_reasigna_paciente_de_otro_usuario(self, user_paciente):
        otro_user = User.objects.create_user(
            username="otro.svc.alpha",
            email="otro.svc@example.com",
            password="x",
            rol="paciente",
        )
        Paciente.objects.create(
            dni="SVC-LINK-3",
            nombre="Z",
            apellido="Z",
            email=user_paciente.email,
            user=otro_user,
        )
        result = ensure_paciente_linked_to_user(user_paciente)
        assert result is None

    def test_no_crea_paciente_automaticamente(self, user_paciente):
        # Sin pacientes coincidentes, el servicio no debe inventar uno.
        assert Paciente.objects.count() == 0
        assert ensure_paciente_linked_to_user(user_paciente) is None
        assert Paciente.objects.count() == 0
