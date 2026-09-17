"""Permisos globales del administrador sin depender de is_staff/superuser."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.permissions import IsMedicoOrAdmin, IsSecretariaOrAdmin


@pytest.mark.parametrize("permission", [IsMedicoOrAdmin, IsSecretariaOrAdmin])
def test_admin_sin_grupos_tiene_acceso(permission):
    groups = Mock()
    groups.filter.return_value.exists.return_value = False
    user = SimpleNamespace(is_authenticated=True, is_superuser=False,
                           is_staff=False, rol="admin", groups=groups)
    assert permission().has_permission(SimpleNamespace(user=user), None)
