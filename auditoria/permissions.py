from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsAuditAdmin(BasePermission):
    """
    Readonly access to audit events.

    Allows:
    - superuser
    - Django staff
    - users with rol == 'admin'
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return (getattr(user, "rol", "") or "").lower() == "admin"

