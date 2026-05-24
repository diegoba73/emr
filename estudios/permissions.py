from rest_framework import permissions

from .access import (
    usuario_puede_crear_estudio,
    usuario_puede_escribir_estudio,
    usuario_puede_ver_estudio,
    usuario_puede_ver_estudio_clinico,
)


class EstudioComplementarioPermission(permissions.BasePermission):
    """Lectura/escritura de estudios complementarios EMR."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            # C6.4.1: secretaría/enfermería/laboratorio → queryset vacío (200), no 403 global.
            return True
        return usuario_puede_escribir_estudio(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            rol = str(getattr(request.user, 'rol', '') or '').lower()
            if rol == 'paciente':
                return usuario_puede_ver_estudio(request.user, obj)
            return usuario_puede_ver_estudio_clinico(request.user, obj)
        action = getattr(view, 'action', None)
        if action in (
            'marcar_realizado',
            'anular',
            'entregar',
            'agregar_archivo',
            'informes',
            'emitir_informe',
            'validar_informe',
            'rectificar_informe',
        ):
            return usuario_puede_ver_estudio_clinico(request.user, obj) and usuario_puede_escribir_estudio(
                request.user
            )
        if obj.es_terminal:
            return False
        return usuario_puede_ver_estudio_clinico(request.user, obj) and usuario_puede_escribir_estudio(
            request.user
        )


class EstudioComplementarioCreatePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and usuario_puede_escribir_estudio(request.user)
