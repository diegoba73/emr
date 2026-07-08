from rest_framework import permissions

from .access import (
    usuario_puede_asignar_turno_estudio,
    usuario_puede_crear_estudio,
    usuario_puede_escribir_estudio,
    usuario_puede_ver_estudio,
    usuario_puede_ver_estudio_clinico,
    usuario_puede_ver_estudios_agenda,
)


class EstudioComplementarioPermission(permissions.BasePermission):
    """Lectura/escritura de estudios complementarios EMR."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return usuario_puede_ver_estudios_agenda(request.user)
        action = getattr(view, 'action', None)
        if action in ('asignar_turno', 'agendar_turno'):
            return usuario_puede_asignar_turno_estudio(request.user)
        return usuario_puede_escribir_estudio(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            rol = str(getattr(request.user, 'rol', '') or '').lower()
            if rol == 'paciente':
                return usuario_puede_ver_estudio(request.user, obj)
            return usuario_puede_ver_estudio_clinico(request.user, obj)
        action = getattr(view, 'action', None)
        if action == 'asignar_turno':
            return usuario_puede_ver_estudio_clinico(request.user, obj) and usuario_puede_asignar_turno_estudio(
                request.user
            )
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
