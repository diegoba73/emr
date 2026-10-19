from rest_framework import permissions

from .access import (
    usuario_puede_asignar_turno_estudio,
    usuario_puede_escribir_estudio,
    usuario_puede_entregar_estudio,
    usuario_puede_marcar_realizado,
    usuario_puede_cerrar_cirugia,
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
            rol = str(getattr(request.user, 'rol', '') or '').lower()
            # Paciente: listado/detalle filtrado a sus estudios ENTREGADO (queryset).
            if rol == 'paciente':
                return True
            return usuario_puede_ver_estudios_agenda(request.user)
        action = getattr(view, 'action', None)
        rol = str(getattr(request.user, 'rol', '') or '').lower()
        if action in ('asignar_turno', 'agendar_turno', 'reprogramar_turno'):
            return usuario_puede_asignar_turno_estudio(request.user)
        if action == 'marcar_realizado':
            return usuario_puede_marcar_realizado(request.user)
        if action == 'cerrar':
            return usuario_puede_cerrar_cirugia(request.user)
        if action == 'enviar_informe':
            return usuario_puede_escribir_estudio(request.user)
        if action == 'entregar':
            return usuario_puede_escribir_estudio(request.user)
        # Alta y resto de escritura: secretaría incluida en usuario_puede_escribir_estudio.
        if action == 'create' or (action is None and request.method == 'POST'):
            return usuario_puede_escribir_estudio(request.user)
        return usuario_puede_escribir_estudio(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            rol = str(getattr(request.user, 'rol', '') or '').lower()
            if rol == 'paciente':
                return usuario_puede_ver_estudio(request.user, obj)
            return usuario_puede_ver_estudio_clinico(request.user, obj)
        action = getattr(view, 'action', None)
        if action == 'enviar_informe':
            return usuario_puede_ver_estudio_clinico(request.user, obj)
        if action in ('asignar_turno', 'reprogramar_turno'):
            return usuario_puede_ver_estudio_clinico(request.user, obj) and usuario_puede_asignar_turno_estudio(
                request.user
            )
        if action == 'cerrar':
            return (
                usuario_puede_ver_estudio_clinico(request.user, obj)
                and usuario_puede_cerrar_cirugia(request.user, obj)
            )
        if action == 'entregar':
            return usuario_puede_entregar_estudio(request.user, obj)
        if action == 'marcar_realizado':
            return (
                usuario_puede_ver_estudio_clinico(request.user, obj)
                and usuario_puede_marcar_realizado(request.user)
            )
        if action in (
            'anular',
            'agregar_archivo',
            'subir_archivo',
            'quitar_archivo',
            'sugerir_informe',
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
        # PATCH genérico: roles con escritura del módulo (incluye secretaría).
        return usuario_puede_ver_estudio_clinico(request.user, obj) and usuario_puede_escribir_estudio(
            request.user
        )


class EstudioComplementarioCreatePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return usuario_puede_escribir_estudio(request.user)
