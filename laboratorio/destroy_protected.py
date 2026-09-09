"""Destroy seguro: ProtectedError → 409 con opción de desactivar."""
from __future__ import annotations

from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response


class ProtectedDestroyMixin:
    """
    Si el DELETE falla por FK PROTECT, responde 409 con can_deactivate=True
    cuando el modelo tiene campo `activo`.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        can_deactivate = hasattr(instance, "activo")
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar porque tiene registros relacionados "
                        "(movimientos, corridas u otros). Podés desactivarlo."
                        if can_deactivate
                        else "No se puede eliminar porque tiene registros relacionados."
                    ),
                    "code": "PROTECTED",
                    "can_deactivate": can_deactivate,
                },
                status=status.HTTP_409_CONFLICT,
            )
