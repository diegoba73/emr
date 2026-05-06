from __future__ import annotations

from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "timestamp",
        "action",
        "entity_type",
        "entity_id",
        "actor",
        "request_id",
        "success",
    )
    list_filter = ("action", "entity_type", "success", "timestamp")
    search_fields = ("entity_type", "entity_id", "request_id", "actor__username", "actor__email")
    ordering = ("-timestamp", "-id")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

