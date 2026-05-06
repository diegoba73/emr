from __future__ import annotations

from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor",
            "actor_username",
            "action",
            "entity_type",
            "entity_id",
            "entity_repr",
            "before_state",
            "after_state",
            "request_id",
            "ip_address",
            "user_agent",
            "module",
            "metadata",
            "success",
            "error_message",
        ]
        read_only_fields = fields

