"""Throttles de autenticación pública (login / registro).

Rates generosos a propósito: frenar spraying sin bloquear operativa clínica
en PCs compartidas. Ajustables vía atributo ``rate`` o tests.
"""
from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class AuthLoginThrottle(SimpleRateThrottle):
    """Límite por IP para POST /api/auth/login/."""

    scope = 'auth_login'
    rate = '30/min'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class AuthRegisterThrottle(SimpleRateThrottle):
    """Límite por IP para registro público de pacientes."""

    scope = 'auth_register'
    rate = '10/min'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
