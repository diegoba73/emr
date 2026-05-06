from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditEventQuerySet(models.QuerySet):
    """
    QuerySet estricto para append-only:

    - ``.delete()`` debe fallar (colección o instancia vía ORM).
    - ``.update()`` debe fallar (no confundir con ``bulk_update()`` de Django, que ejecuta SQL UPDATE directo).
    """

    def delete(self):
        raise ValidationError("AuditEvent es append-only: no se permite DELETE en queryset.delete()")

    def update(self, **kwargs):
        raise ValidationError("AuditEvent es append-only: no se permite queryset.update()")


AuditEventManager = models.Manager.from_queryset(AuditEventQuerySet)


class AuditEvent(models.Model):
    """
    Append-only audit event.

    This is the first "enterprise foundation" layer:
    - Centralized, transversal, reusable
    - Stores request tracing data + before/after snapshots
    - Does NOT attempt clinical-grade versioning or event sourcing
    """

    objects = AuditEventManager()

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    action = models.CharField(max_length=50, db_index=True)
    module = models.CharField(max_length=100, blank=True, default="")

    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True, default="")

    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)

    request_id = models.CharField(max_length=36, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    metadata = models.JSONField(null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "auditoria_auditevent"
        ordering = ["-timestamp", "-id"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="audit_entity_idx"),
            models.Index(fields=["actor"], name="audit_actor_idx"),
            models.Index(fields=["action"], name="audit_action_idx"),
            models.Index(fields=["request_id"], name="audit_request_idx"),
        ]

    def clean(self):
        if not self.request_id:
            raise ValidationError({"request_id": "request_id es obligatorio"})
        if not self.action:
            raise ValidationError({"action": "action es obligatorio"})
        if not self.entity_type:
            raise ValidationError({"entity_type": "entity_type es obligatorio"})

    def save(self, *args, **kwargs):
        # Append-only: never allow updates.
        if self.pk and not self._state.adding:
            raise ValidationError("AuditEvent es append-only: no se permite UPDATE")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("AuditEvent es append-only: no se permite DELETE")

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.action} {self.entity_type}:{self.entity_id}"
