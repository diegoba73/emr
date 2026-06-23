"""Tests de auditoría en altas y modificaciones de ``Paciente`` vía API activa.

Los eventos se persisten con ``transaction.on_commit`` cuando hay bloque
``atomic`` (típico en tests con rollback). Usar ``captureOnCommitCallbacks`` como
en ``laboratorio/tests`` y ``turnos/tests``.
"""
from datetime import date
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
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


def _payload_create(dni_suffix):
    return {
        "dni": f"AUD-{dni_suffix}",
        "nombre": "Ana",
        "apellido": "Audit",
        "fecha_nacimiento": "1988-03-20",
    }


class TestPacienteAuditoriaAPI(TestCase):
    """Verifica que ``perform_create`` / ``perform_update`` generan ``AuditEvent``."""

    def test_post_create_genera_audit_event_create(self):
        admin = _admin("admin.audit.create")
        client = APIClient()
        client.force_authenticate(user=admin)
        payload = _payload_create("CRT-0")

        with self.captureOnCommitCallbacks(execute=True):
            response = client.post("/api/pacientes/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        paciente_id = response.data["id"]

        ev = (
            AuditEvent.objects.filter(
                entity_type=Paciente._meta.label,
                entity_id=str(paciente_id),
                action="CREATE",
                module="pacientes",
            )
            .order_by("-timestamp", "-id")
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertEqual(ev.actor_id, admin.id)
        self.assertIsNone(ev.before_state)
        self.assertIsNotNone(ev.after_state)
        self.assertEqual(ev.metadata.get("view"), "PacienteViewSet.perform_create")

    def test_patch_genera_audit_event_update(self):
        admin = _admin("admin.audit.patch")
        paciente = Paciente.objects.create(
            dni="AUD-PATCH-0",
            nombre="Antes",
            apellido="Apellido",
            telefono="111",
        )
        client = APIClient()
        client.force_authenticate(user=admin)

        with self.captureOnCommitCallbacks(execute=True):
            response = client.patch(
                f"/api/pacientes/{paciente.id}/",
                {"telefono": "222", "observaciones": "Cambio auditado"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        ev = (
            AuditEvent.objects.filter(
                entity_type=Paciente._meta.label,
                entity_id=str(paciente.id),
                action="UPDATE",
                module="pacientes",
            )
            .order_by("-timestamp", "-id")
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertEqual(ev.actor_id, admin.id)
        self.assertIsNotNone(ev.before_state)
        self.assertIsNotNone(ev.after_state)
        self.assertEqual(ev.metadata.get("view"), "PacienteViewSet.perform_update")
        self.assertEqual(ev.after_state.get("telefono"), "<dato sensible redactado>")
        self.assertNotIn("222", json.dumps(ev.after_state))
        self.assertNotIn("Cambio auditado", json.dumps(ev.after_state))

    def test_put_genera_audit_event_update(self):
        admin = _admin("admin.audit.put")
        paciente = Paciente.objects.create(
            dni="AUD-PUT-0",
            nombre="Put",
            apellido="Test",
            fecha_nacimiento=date(1990, 1, 1),
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        payload = _payload_create("PUT-1")
        payload["dni"] = "AUD-PUT-0"
        payload["telefono"] = "333444555"

        with self.captureOnCommitCallbacks(execute=True):
            response = client.put(
                f"/api/pacientes/{paciente.id}/",
                payload,
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        ev = (
            AuditEvent.objects.filter(
                entity_type=Paciente._meta.label,
                entity_id=str(paciente.id),
                action="UPDATE",
                module="pacientes",
            )
            .order_by("-timestamp", "-id")
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertEqual(ev.metadata.get("view"), "PacienteViewSet.perform_update")
        self.assertNotIn("333444555", json.dumps(ev.after_state or {}))

    def test_create_entity_repr_sin_phi(self):
        admin = _admin("admin.audit.repr")
        client = APIClient()
        client.force_authenticate(user=admin)
        payload = _payload_create("REPR-0")

        with self.captureOnCommitCallbacks(execute=True):
            response = client.post("/api/pacientes/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        paciente_id = response.data["id"]
        ev = AuditEvent.objects.filter(
            entity_type=Paciente._meta.label,
            entity_id=str(paciente_id),
            action="CREATE",
        ).first()
        self.assertIsNotNone(ev)
        self.assertEqual(ev.entity_repr, f"Paciente #{paciente_id}")
        self.assertNotIn("Ana", ev.entity_repr)
        self.assertNotIn("AUD-REPR-0", ev.entity_repr)

    def test_create_no_genera_evento_delete(self):
        """DELETE API está bloqueado; no debe existir auditoría DELETE en este flujo."""
        admin = _admin("admin.audit.nodelete")
        paciente = Paciente.objects.create(dni="AUD-DEL-0", nombre="X", apellido="Y")
        client = APIClient()
        client.force_authenticate(user=admin)

        with self.captureOnCommitCallbacks(execute=True):
            response = client.delete(f"/api/pacientes/{paciente.id}/")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(
            AuditEvent.objects.filter(
                entity_type=Paciente._meta.label,
                entity_id=str(paciente.id),
                action="DELETE",
            ).exists()
        )
