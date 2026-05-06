from __future__ import annotations

from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend

from .filters import AuditEventFilter
from .models import AuditEvent
from .permissions import IsAuditAdmin
from .serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Readonly API for audit events.
    """

    queryset = AuditEvent.objects.select_related("actor").all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuditAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AuditEventFilter
    ordering = ["-timestamp", "-id"]

