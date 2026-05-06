from __future__ import annotations

import logging
from typing import Any

from django.db import models, transaction

from .context import get_ip_address, get_request_id, get_user_agent
from .models import AuditEvent
from .sanitizer import enforce_max_json_payload, sanitize_dict_keys
from .snapshot import safe_model_snapshot

logger = logging.getLogger(__name__)

# Nunca crear eventos sobre el propio almacén de auditoría ni modelos blacklist explícitos.
_BLACKLIST_META_LABEL_LOWER = frozenset(
    {
        "auditoria.auditevent",
    }
)


def _entity_blocked(instance: models.Model | None, entity_type: str | None) -> bool:
    if instance is not None:
        try:
            if instance._meta.label_lower in _BLACKLIST_META_LABEL_LOWER:
                return True
        except Exception:
            return True
    if entity_type:
        et = entity_type.strip().lower()
        normalized = et.replace(" ", "")
        if normalized in _BLACKLIST_META_LABEL_LOWER or normalized == "auditoria.auditevent":
            return True
    return False


def _entity_type_for(instance: models.Model | None, entity_type: str | None) -> str:
    if entity_type:
        return entity_type
    if instance is None:
        return "global"
    return instance._meta.label  # e.g. "turnos.Turno"


def _entity_id_for(instance: models.Model | None, entity_id: str | int | None) -> str | None:
    if entity_id is not None:
        return str(entity_id)
    if instance is None:
        return None
    pk = getattr(instance, "pk", None)
    return str(pk) if pk is not None else None


def _entity_repr_for(instance: models.Model | None, entity_repr: str | None) -> str:
    if entity_repr is not None:
        return entity_repr
    if instance is None:
        return ""
    try:
        s = str(instance)
    except Exception:
        s = instance.__class__.__name__
    return (s or "")[:255]


def _sanitize_audit_payload(before: Any, after: Any, metadata: Any) -> tuple[Any, Any, Any]:
    b = sanitize_dict_keys(before) if before is not None else None
    a = sanitize_dict_keys(after) if after is not None else None
    meta = sanitize_dict_keys(metadata) if metadata is not None else None
    b = enforce_max_json_payload(b) if b is not None else None
    a = enforce_max_json_payload(a) if a is not None else None
    meta = enforce_max_json_payload(meta) if meta is not None else None
    return b, a, meta


def _schedule_audit_persist(do_create_fn) -> None:
    """Dentro de atomic: persistir sólo después de commit estable. Fuera de atomic: inmediato."""
    conn = transaction.get_connection()
    if conn.in_atomic_block:
        transaction.on_commit(do_create_fn)
    else:
        do_create_fn()


def log_event(
    *,
    action: str,
    actor=None,
    entity: models.Model | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    entity_repr: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    module: str | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> AuditEvent | None:
    """
    Registro append-only best-effort. Fallos NO deben cortar flujo principal.

    **Post-commit (seguridad transaccional):**
    cuando la llamada ocurre dentro de ``transaction.atomic()``, la fila
    ``AuditEvent`` se inserta vía ``transaction.on_commit``, de modo que un
    rollback borre tanto la operación clínica como la auditoría asociada.

    **Sin atomic externo:** la inserción es inmediata (servicios de comando,
    management commands fuera de transacciones explícitas).

    Si el evento se difiere, esta función suele devolver ``None`` (el objeto
    aún no existe en BD al salir).
    """
    try:
        if _entity_blocked(entity, entity_type):
            logger.warning("audit_service: omitido (blacklist) entity=%s entity_type=%s", entity, entity_type)
            return None

        rid = get_request_id() or "missing"
        ip_capture = get_ip_address()
        ua_capture = get_user_agent() or ""

        # IDs capturados ahora por si el objeto actor muta antes del commit.
        actor_id_capture = getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None

        bt, af, mt = _sanitize_audit_payload(before, after, metadata)

        ent_type_final = _entity_type_for(entity, entity_type)
        ent_id_final = _entity_id_for(entity, entity_id)
        ent_repr_final = _entity_repr_for(entity, entity_repr)

        outcome: dict[str, Any | None] = {"event": None}

        def _do_create() -> None:
            try:
                ev = AuditEvent.objects.create(
                    actor_id=actor_id_capture,
                    action=str(action),
                    module=(module or "")[:100],
                    entity_type=ent_type_final,
                    entity_id=ent_id_final,
                    entity_repr=ent_repr_final,
                    before_state=bt,
                    after_state=af,
                    request_id=str(rid),
                    ip_address=ip_capture,
                    user_agent=(ua_capture or "")[:3900],
                    metadata=mt,
                    success=bool(success),
                    error_message=(str(error_message)[:4000] if error_message is not None else None),
                )
                outcome["event"] = ev
            except Exception as e:  # noqa: BLE001
                logger.exception("Audit logging failed (ignored): %s", e)

        _schedule_audit_persist(_do_create)

        # Con on_commit aplazado, el objeto aún puede no estar creado.
        return outcome["event"]

    except Exception as e:
        logger.exception("Audit logging failed (ignored): %s", e)
        return None


def log_create(*, actor=None, entity: models.Model, module: str | None = None, metadata: dict[str, Any] | None = None):
    return log_event(
        action="CREATE",
        actor=actor,
        entity=entity,
        before=None,
        after=safe_model_snapshot(entity),
        metadata=metadata,
        module=module,
    )


def log_update(
    *,
    actor=None,
    entity: models.Model,
    before_instance: models.Model | None = None,
    before: dict[str, Any] | None = None,
    module: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    if before is None and before_instance is not None:
        before = safe_model_snapshot(before_instance)
    return log_event(
        action="UPDATE",
        actor=actor,
        entity=entity,
        before=before,
        after=safe_model_snapshot(entity),
        metadata=metadata,
        module=module,
    )


def log_delete(*, actor=None, entity_type: str, entity_id: str | int, entity_repr: str = "", module: str | None = None, metadata: dict[str, Any] | None = None):
    return log_event(
        action="DELETE",
        actor=actor,
        entity=None,
        entity_type=entity_type,
        entity_id=str(entity_id),
        entity_repr=entity_repr,
        before=None,
        after=None,
        metadata=metadata,
        module=module,
    )
