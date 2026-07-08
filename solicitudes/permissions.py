"""Permisos por acción para solicitudes genéricas EMR (PERM-01 / INT-01)."""

from __future__ import annotations

from rest_framework import permissions

from api.permissions import get_normalized_role


def user_medico(user):
    try:
        return user.medico
    except Exception:
        return None


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and (
        user.is_superuser or get_normalized_role(user) == 'admin'
    ))


def medico_linked_to_solicitud(user, obj) -> bool:
    medico = user_medico(user)
    if not medico:
        return False
    if getattr(obj, 'medico_solicitante_id', None) == medico.pk:
        return True
    if getattr(obj, 'creado_por_id', None) == user.pk:
        return True
    if hasattr(obj, 'medicos_asignados') and obj.medicos_asignados.filter(pk=medico.pk).exists():
        return True
    return False


def paciente_owns_solicitud(user, obj) -> bool:
    try:
        paciente = user.paciente
    except Exception:
        return False
    return getattr(obj, 'paciente_id', None) == paciente.pk


_READ_ACTIONS = frozenset({
    'list',
    'retrieve',
    'estadisticas',
    'pendientes',
    'vencidas',
    'mias',
    'proximas_vencer',
})

_WRITE_ACTIONS = frozenset({'update', 'partial_update'})

_ADMIN_ONLY_ACTIONS = frozenset({
    'destroy',
    'cambiar_estado',
    'reabrir',
    'marcar_como_completada',
    'sincronizar_lims',
    'enviar_lims',
})


class SolicitudPermission(permissions.BasePermission):
    """
    Matriz PERM-01: solicitudes genéricas EMR (no LIMS nativo).

    - admin/superuser: operación completa salvo PHI en auditoría.
    - médico: lectura/escritura limitada solo en solicitudes vinculadas; sin LIMS ni estados críticos.
    - secretaría: solo lectura (listado/detalle); sin LIMS ni cambio de estado.
    - paciente: solo lectura de propias solicitudes.
    - laboratorio/enfermería/sin rol/anónimo: sin acceso.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if is_admin(user):
            return True

        role = get_normalized_role(user)
        action = getattr(view, 'action', None)

        if not role or role in ('laboratorio', 'enfermeria'):
            return False

        if action in _READ_ACTIONS:
            return role in ('admin', 'secretaria', 'medico', 'paciente')

        if action == 'create':
            return role in ('admin', 'medico')

        if action in _WRITE_ACTIONS:
            return role in ('admin', 'medico')

        if action in _ADMIN_ONLY_ACTIONS:
            return False

        if action == 'cancelar':
            return role in ('admin', 'medico')

        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if is_admin(user):
            return True

        role = get_normalized_role(user)
        action = getattr(view, 'action', None)

        if role == 'secretaria':
            return action in _READ_ACTIONS

        if role == 'medico':
            if not medico_linked_to_solicitud(user, obj):
                return False
            if action in _ADMIN_ONLY_ACTIONS:
                return False
            return action in _READ_ACTIONS | _WRITE_ACTIONS | frozenset({'cancelar'})

        if role == 'paciente':
            if not paciente_owns_solicitud(user, obj):
                return False
            return action in _READ_ACTIONS

        return False
