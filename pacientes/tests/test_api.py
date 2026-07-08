"""Tests de integración API para el bloque ``pacientes``.

Cubren:

- Identidad mínima al crear vía POST (dni, nombre, apellido, fecha_nacimiento).
- Normalización de nombre/apellido al crear vía POST.
- Búsqueda inteligente respetando filtros de rol (admin vs médico vs paciente).
- Privacidad: ``?all=true`` no debe escalar acceso para un médico.
- DELETE físico bloqueado para todos.
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.models import Paciente

User = get_user_model()


def _payload_create(**overrides):
    base = {
        "dni": "API-BASE-0",
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


def _laboratorio_user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
        rol="laboratorio",
        is_staff=False,
    )


@pytest.mark.django_db
class TestPacienteAPICreacionIdentidadMinima:
    def test_post_sin_nombre_400(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.noname"))
        data = _payload_create(dni="API-NONAME-0")
        del data["nombre"]
        response = client.post("/api/pacientes/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "nombre" in response.data

    def test_post_sin_apellido_400(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.noape"))
        data = _payload_create(dni="API-NOAPE-0")
        del data["apellido"]
        response = client.post("/api/pacientes/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "apellido" in response.data

    def test_post_sin_fecha_nacimiento_400(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.nofnac"))
        data = _payload_create(dni="API-NOFNAC-0")
        del data["fecha_nacimiento"]
        response = client.post("/api/pacientes/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "fecha_nacimiento" in response.data

    def test_post_valido_201(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.ok"))
        data = _payload_create(dni="API-OK-0")
        response = client.post("/api/pacientes/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        paciente = Paciente.objects.get(dni="API-OK-0")
        assert paciente.nombre == "Juan"
        assert paciente.fecha_nacimiento == date(1990, 5, 15)

    def test_patch_legacy_sin_reenviar_identidad(self):
        paciente = Paciente.objects.create(dni="API-LEG-0")
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.patchleg"))
        response = client.patch(
            f"/api/pacientes/{paciente.id}/",
            {"telefono": "555"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        paciente.refresh_from_db()
        assert paciente.telefono == "555"

    def test_retrieve_legacy_con_nulos_200(self):
        paciente = Paciente.objects.create(dni="API-LEG-RET-0")
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.retleg"))
        response = client.get(f"/api/pacientes/{paciente.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["dni"] == "API-LEG-RET-0"


@pytest.mark.django_db
class TestPacienteAPINormalizacion:
    def test_normalizacion_nombre_apellido(self):
        client = APIClient()
        client.force_authenticate(user=_admin("admin.api.norm"))

        data = _payload_create(
            dni="API-NRM-0",
            nombre="  juan  ",
            apellido="  perez  ",
        )
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

    def test_laboratorio_lista_pacientes(self):
        Paciente.objects.create(dni="PRIV-LAB-0", nombre="A", apellido="B")
        client = APIClient()
        client.force_authenticate(user=_laboratorio_user("lab.priv.list"))
        response = client.get("/api/pacientes/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_laboratorio_is_staff_lista_pacientes_sin_bypass_emr(self):
        """Operadores LIMS con is_staff no escalan a PHI vía staff; lectura operativa por rol."""
        Paciente.objects.create(dni="PRIV-LAB-ST-0", nombre="Ana", apellido="Demo")
        user = User.objects.create_user(
            username="lab.staff.phi",
            email="lab.staff@example.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/pacientes/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_laboratorio_is_staff_buscar_pacientes(self):
        Paciente.objects.create(dni="PRIV-LAB-ST-1", nombre="Juan", apellido="Perez")
        user = User.objects.create_user(
            username="lab.staff.busq",
            email="lab.staff.busq@example.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/pacientes/buscar/?q=Perez")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_laboratorio_is_staff_retrieve_paciente(self):
        paciente = Paciente.objects.create(dni="PRIV-LAB-ST-2", nombre="X", apellido="Y")
        user = User.objects.create_user(
            username="lab.staff.det",
            email="lab.staff.det@example.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/pacientes/{paciente.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == paciente.id


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


@pytest.mark.django_db
class TestPacienteAPIReadOnlyDemographics:
    def test_paciente_no_puede_patch_propio_perfil(self):
        user = _paciente_user("pac.readonly.patch")
        paciente = Paciente.objects.create(
            dni="PAC-RO-1",
            nombre="Ana",
            apellido="Paciente",
            user=user,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/pacientes/{paciente.id}/",
            {"telefono": "1111111111"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        paciente.refresh_from_db()
        assert paciente.telefono != "1111111111"

    def test_paciente_no_puede_crear_paciente(self):
        user = _paciente_user("pac.readonly.create")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/pacientes/", _payload_create(dni="PAC-RO-2"), format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
