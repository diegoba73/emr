"""Resolución de internación y roles de escritura de formularios HC."""
from __future__ import annotations

from rest_framework.exceptions import NotFound, PermissionDenied

from api.permissions import get_normalized_role
from usuarios.roles import ROLES_INTERNACION

from .models import Internacion


def internacion_para_usuario(request, internacion_pk) -> Internacion:
    try:
        internacion = Internacion.objects.get(pk=internacion_pk)
    except Internacion.DoesNotExist as exc:
        raise NotFound('No Internacion matches the given query.') from exc

    user = request.user
    if user.is_superuser or get_normalized_role(user) == 'admin':
        return internacion

    rol = get_normalized_role(user)
    if rol not in ROLES_INTERNACION:
        raise PermissionDenied()
    if not internacion.activo:
        raise PermissionDenied('No puede acceder a internaciones inactivas.')
    return internacion


def puede_escribir_hc(request, write_roles: frozenset[str]) -> bool:
    user = request.user
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return get_normalized_role(user) in write_roles
