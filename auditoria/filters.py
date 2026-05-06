from __future__ import annotations

import django_filters

from .models import AuditEvent


class AuditEventFilter(django_filters.FilterSet):
    entity_type = django_filters.CharFilter(field_name="entity_type", lookup_expr="iexact")
    entity_id = django_filters.CharFilter(field_name="entity_id", lookup_expr="exact")
    actor = django_filters.NumberFilter(field_name="actor_id")
    action = django_filters.CharFilter(field_name="action", lookup_expr="iexact")
    request_id = django_filters.CharFilter(field_name="request_id", lookup_expr="exact")

    fecha_desde = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gte")
    fecha_hasta = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = AuditEvent
        fields = [
            "entity_type",
            "entity_id",
            "actor",
            "action",
            "request_id",
            "fecha_desde",
            "fecha_hasta",
        ]

