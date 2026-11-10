"""Throttle generoso de login/registro público (hardening A+1)."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from api.throttles import AuthLoginThrottle, AuthRegisterThrottle

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_login_throttle_returns_429_after_limit(api_client):
    User.objects.create_user(username='throttle_user', password='ThrottlePass123!')
    original = AuthLoginThrottle.rate
    AuthLoginThrottle.rate = '2/min'
    cache.clear()
    try:
        r1 = api_client.post(
            '/api/auth/login/',
            {'username': 'throttle_user', 'password': 'wrong'},
            format='json',
        )
        r2 = api_client.post(
            '/api/auth/login/',
            {'username': 'throttle_user', 'password': 'wrong'},
            format='json',
        )
        r3 = api_client.post(
            '/api/auth/login/',
            {'username': 'throttle_user', 'password': 'wrong'},
            format='json',
        )
        assert r1.status_code == status.HTTP_401_UNAUTHORIZED
        assert r2.status_code == status.HTTP_401_UNAUTHORIZED
        assert r3.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    finally:
        AuthLoginThrottle.rate = original
        cache.clear()


@pytest.mark.django_db
def test_login_exitoso_sigue_funcionando_bajo_throttle_generoso(api_client):
    User.objects.create_user(username='ok_user', password='OkPass123!')
    cache.clear()
    r = api_client.post(
        '/api/auth/login/',
        {'username': 'ok_user', 'password': 'OkPass123!'},
        format='json',
    )
    assert r.status_code == status.HTTP_200_OK
    assert r.data.get('message') == 'Login exitoso'


@pytest.mark.django_db
def test_register_throttle_returns_429_after_limit(api_client):
    original = AuthRegisterThrottle.rate
    AuthRegisterThrottle.rate = '1/min'
    cache.clear()
    try:
        payload = {
            'username': 'reg1',
            'email': 'reg1@test.com',
            'password': 'Weak',  # fallará validación; igual cuenta para throttle
            'first_name': 'A',
            'last_name': 'B',
            'dni': 'REG-1',
        }
        r1 = api_client.post('/api/auth/register/patient/', payload, format='json')
        r2 = api_client.post('/api/auth/register/patient/', payload, format='json')
        assert r1.status_code != status.HTTP_429_TOO_MANY_REQUESTS
        assert r2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    finally:
        AuthRegisterThrottle.rate = original
        cache.clear()
