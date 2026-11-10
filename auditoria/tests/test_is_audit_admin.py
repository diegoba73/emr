"""IsAuditAdmin alineado con FE canAccessAuditoria (excluye operadores LIMS)."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'rol,is_staff,allowed',
    [
        ('admin', True, True),
        ('admin', False, True),
        ('medico', True, True),
        ('enfermeria', True, True),
        ('laboratorio', True, False),
        ('bioquimico', True, False),
        ('medico', False, False),
    ],
)
def test_auditoria_events_acl(api_client, rol, is_staff, allowed):
    user = User.objects.create_user(
        username=f'audit_{rol}_{is_staff}',
        password='x',
        rol=rol,
        is_staff=is_staff,
    )
    api_client.force_authenticate(user=user)
    r = api_client.get('/api/auditoria/events/')
    if allowed:
        assert r.status_code == status.HTTP_200_OK
    else:
        assert r.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_superuser_accede_auditoria(api_client):
    user = User.objects.create_superuser(
        username='audit_su',
        email='su@test.com',
        password='x',
    )
    api_client.force_authenticate(user=user)
    r = api_client.get('/api/auditoria/events/')
    assert r.status_code == status.HTTP_200_OK
