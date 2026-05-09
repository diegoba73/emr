"""Tests de integración API para el bloque ``pacientes``.

Cubren:

- Normalización de nombre/apellido al crear vía POST.
- Búsqueda inteligente respetando filtros de rol (admin vs médico vs paciente).
- Privacidad: ``?all=true`` no debe escalar acceso para un médico.
- DELETE físico bloqueado para todos.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.models import Paciente

User = get_user_model()


def _admin(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
        rol="admin",
        is_staff=True,
    )


def _medico_user(username, *, vincular_medico=False):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
        rol="medico",
    )
    if vincular_medico:
        from medicos.models import Especialidad, Medico

        especialidad, _ = Especialidad.objects.get_or_create(
            nombre=f"Esp Pacientes Test {username}"
        )
        Medico.objects.create(
            user=user,
            nombre="Dr. Test",
            apellido="Médico",
            matricula=f"MAT-{username[:8]}",
            especialidad=especialidad,
        )
    return user


def _paciente_user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
        rol="paciente",
    )


@pytest.mark.django_db
class TestPacienteAPINormalizacion:
    def test_normalizacion_nombre_apellido(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.norm"))

        data = {"dni": "API-NRM-0", "nombre": "  juan  ", "apellido": "  perez  "}
        response = client.post("/api/pacientes/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        paciente = Paciente.objects.get(dni="API-NRM-0")
        assert paciente.nombre == "Juan"
        assert paciente.apellido == "Perez"


@pytest.mark.django_db
class TestPacienteAPIBusquedaPermisos:
    """La búsqueda debe respetar ``get_queryset()``: nunca expone más datos
    que el rol permite.
    """

    def setup_method(self):
        Paciente.objects.create(dni="API-BUSQ-12345", nombre="Juan", apellido="Perez")
        Paciente.objects.create(dni="API-BUSQ-22222", nombre="Pedro", apellido="Perez")
        Paciente.objects.create(dni="API-BUSQ-33333", nombre="Carlos", apellido="Perez")

    def test_admin_ve_todos_los_resultados_por_apellido(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.busq"))

        response = client.get("/api/pacientes/buscar/?q=Perez")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 3
        assert all("Perez" in r["apellido"] for r in results)

    def test_admin_busca_por_dni_parcial(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.dni"))

        # ``q`` numérico activa la rama por DNI; usamos solo dígitos del DNI.
        response = client.get("/api/pacientes/buscar/?q=22222")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert any(r["dni"] == "API-BUSQ-22222" for r in results)

    def test_busqueda_no_encontrada_devuelve_lista_vacia(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.zero"))

        response = client.get("/api/pacientes/buscar/?q=NoExisteApellido")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_busqueda_sin_parametro_q(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.req"))

        response = client.get("/api/pacientes/buscar/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data


@pytest.mark.django_db
class TestPacienteAPIPrivacidad:
    """Reglas de privacidad por rol."""

    def test_medico_sin_vinculos_no_ve_pacientes(self):
        Paciente.objects.create(dni="PRIV-MED-0", nombre="A", apellido="B")
        Paciente.objects.create(dni="PRIV-MED-1", nombre="C", apellido="D")
        user = _medico_user("medico.priv.solo", vincular_medico=True)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/pacientes/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_all_true_no_escala_para_medico(self):
        """``?all=true`` no debe convertir a un médico en lector global."""
        Paciente.objects.create(dni="PRIV-ALL-0", nombre="A", apellido="B")
        user = _medico_user("medico.priv.all", vincular_medico=True)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/pacientes/?all=true")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_paciente_solo_ve_su_propia_ficha(self):
        propio_user = _paciente_user("paciente.priv.self")
        propia = Paciente.objects.create(
            dni="PRIV-PAC-0", nombre="Yo", apellido="Mismo", user=propio_user
        )
        Paciente.objects.create(dni="PRIV-PAC-1", nombre="Otro", apellido="Persona")

        client = APIClient()
        client.force_authenticate(user=propio_user)
        response = client.get("/api/pacientes/")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["id"] == propia.id

    def test_usuario_sin_rol_relevante_recibe_lista_vacia(self):
        Paciente.objects.create(dni="PRIV-NONE-0", nombre="A", apellido="B")
        user = User.objects.create_user(
            username="rol.desconocido",
            email="raro@example.com",
            password="x",
            rol="otro",
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/pacientes/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []


@pytest.mark.django_db
class TestPacienteAPIDelete:
    def test_delete_fisico_bloqueado_para_admin(self):
        paciente = Paciente.objects.create(dni="DEL-ADM-0", nombre="X", apellido="Y")
        client = APIClient()
        client.force_authenticate(user=_admin("admin.delete.block"))

        response = client.delete(f"/api/pacientes/{paciente.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Paciente.objects.filter(pk=paciente.pk).exists()

    def test_delete_fisico_bloqueado_para_medico(self):
        paciente = Paciente.objects.create(dni="DEL-MED-0", nombre="X", apellido="Y")
        client = APIClient()
        client.force_authenticate(
            user=_medico_user("medico.delete.block", vincular_medico=True)
        )

        response = client.delete(f"/api/pacientes/{paciente.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Paciente.objects.filter(pk=paciente.pk).exists()
