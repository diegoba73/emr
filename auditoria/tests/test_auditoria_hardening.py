"""Hardening: transacciones, blacklist, sanitización, append-only, snapshots."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.audit_service import log_event
from auditoria.models import AuditEvent
from auditoria.sanitizer import enforce_max_json_payload, sanitize_dict_keys
from auditoria.snapshot import safe_model_snapshot


@pytest.mark.django_db
def test_audit_not_persisted_on_rollback():
    """Fallo dentro de atomic: ``on_commit`` no corre → ninguna fila nueva."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admin = User.objects.create_user(username="rb1", password="x", rol="admin")

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            log_event(
                action="CREATE",
                actor=admin,
                entity=None,
                entity_type="demo.Dummy",
                entity_id="999",
                entity_repr="rollback test",
            )
            raise RuntimeError("force rollback")

    assert not AuditEvent.objects.filter(entity_type="demo.Dummy", entity_id="999").exists()


@pytest.mark.django_db(transaction=True)
def test_audit_visible_after_outer_commit():
    """
    Confirmación de comportamiento esperado cuando la transacción confirma
    (en este modo de test el commit existe de forma efectiva para la sesión).
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admin = User.objects.create_user(username="rb2", password="x", rol="admin")

    from auditoria.tests.compat import capture_on_commit_callbacks

    with capture_on_commit_callbacks(execute=True):
        with transaction.atomic():
            log_event(
                action="CREATE",
                actor=admin,
                entity=None,
                entity_type="demo.DummyOk",
                entity_id="1",
                entity_repr="ok",
            )

    assert AuditEvent.objects.filter(entity_type="demo.DummyOk", entity_id="1").exists()


@pytest.mark.django_db
def test_blacklist_skips_wrapping_audit_entity():
    """Nunca debe generarse auditoría cuando ``entity`` es ``AuditEvent``."""

    from django.contrib.auth import get_user_model

    User = get_user_model()
    admin = User.objects.create_user(username="bl1", password="x", rol="admin")

    ev_first = AuditEvent.objects.create(
        action="CREATE",
        entity_type="turnos.Turno",
        entity_id="1",
        entity_repr="x",
        request_id="r0",
    )
    count_before = AuditEvent.objects.count()
    rv = log_event(action="META", actor=admin, entity=ev_first)

    assert rv is None
    assert AuditEvent.objects.count() == count_before


@pytest.mark.django_db
def test_sanitize_redacts_sensitive_keys():
    d = sanitize_dict_keys(
        {
            "authorization": "Bearer secret",
            "nested": {"csrf_token": "abc", "ok": 1},
        }
    )
    assert d["authorization"] == "<redacted>"
    assert d["nested"]["csrf_token"] == "<redacted>"
    assert d["nested"]["ok"] == 1


@pytest.mark.django_db
def test_enforce_max_json_payload_caps():
    import json

    blob = {"k": "x" * 200_000}
    lim = 2_000
    out = enforce_max_json_payload(blob, max_json_bytes=lim)
    assert len(json.dumps(out, separators=(",", ":"), default=str).encode("utf-8")) <= lim + 128


@pytest.mark.django_db
def test_append_only_save_delete_and_queryset_update():
    ev = AuditEvent.objects.create(
        action="CREATE",
        entity_type="turnos.Turno",
        entity_id="9",
        entity_repr="",
        request_id="req-a",
    )

    ev.action = "UPDATE"
    with pytest.raises(ValidationError):
        ev.save()

    with pytest.raises(ValidationError):
        ev.delete()

    with pytest.raises(ValidationError):
        AuditEvent.objects.filter(pk=ev.pk).update(action="BAD")

    # queryset.delete(): en algunos entornos Django usa DELETE SQL rápido y puede no
    # pasar por QuerySet.delete() — mitigación en docs (permisos/trigger BD).


@pytest.mark.django_db
def test_bulk_update_blocked_like_queryset_update():
    """
    ``bulk_update`` delega en ``QuerySet.update()``; el QuerySet append-only
    de ``AuditEvent`` bloquea ese camino (además de ``save()`` / ``delete()``).
    """
    ev = AuditEvent.objects.create(
        action="CREATE",
        entity_type="x.T",
        entity_id="1",
        entity_repr="",
        request_id="req-bu",
    )
    ev.action = "SHOULD_CHANGE"
    # Encapsular: el fallo de ``update()`` no debe dejar la conexión marcada como errónea.
    with transaction.atomic():
        with pytest.raises(ValidationError):
            AuditEvent.objects.bulk_update([ev], ["action"])
    ev.refresh_from_db()
    assert ev.action == "CREATE"


@pytest.mark.django_db
def test_snapshot_file_placeholder_not_binary_payload():
    from archivos_medicos.models import ArchivoMedico
    from pacientes.models import Paciente

    p = Paciente.objects.create(dni="snapf1", nombre="N", apellido="A")
    am = ArchivoMedico.objects.create(
        paciente=p,
        titulo="t",
        tipo_archivo="PDF",
        descripcion=("d" * 12_000),
        archivo=None,
    )
    snap = safe_model_snapshot(am)
    assert "<file" in str(snap.get("archivo", "")).lower() or snap.get("archivo") is None
    assert snap.get("descripcion") == "<texto clínico redactado>"
