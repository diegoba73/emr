from __future__ import annotations

from rest_framework.permissions import BasePermission

from usuarios.roles import ROLES_LIMS_OPERADOR


class IsAuditAdmin(BasePermission):
    """
    Readonly access to audit events.

    Alineado con FE ``canAccessAuditoria``:
    - superuser
    - Django staff de roles no-LIMS
    - users with rol == 'admin'
    - operadores LIMS (laboratorio/bioquimico) denegados aunque is_staff=True
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        rol = (getattr(user, "rol", "") or "").lower()
        if rol in ROLES_LIMS_OPERADOR:
            return False
        if user.is_staff:
            return True
        return rol == "admin"

