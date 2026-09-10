"""Autenticación por token de gateway de analizadores."""
from __future__ import annotations

import secrets

from django.conf import settings
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed


HEADER = "X-LIMS-Instrument-Token"


class InstrumentGatewayUser:
    """Actor sintético para el gateway (sin fila User)."""

    pk = None
    id = None
    is_authenticated = True
    is_anonymous = False
    is_active = True
    is_staff = False
    is_superuser = False
    rol = "laboratorio"
    username = "__instrumento__"

    def __str__(self) -> str:
        return self.username


def extract_instrument_token(request) -> str:
    header = request.headers.get(HEADER) or request.META.get("HTTP_X_LIMS_INSTRUMENT_TOKEN") or ""
    if header:
        return str(header).strip()
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("instrument "):
        return auth[11:].strip()
    return ""


def actor_usuario(user):
    """None si el actor no es un User persistido (token de gateway)."""
    if user is None:
        return None
    if not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "pk", None) is None:
        return None
    return user


def token_configurado() -> str:
    return (getattr(settings, "LIMS_INSTRUMENT_TOKEN", "") or "").strip()


class InstrumentTokenAuthentication(BaseAuthentication):
    """Si el header está presente, valida el token; si no, delega (None)."""

    def authenticate(self, request):
        raw = extract_instrument_token(request)
        if not raw:
            return None
        expected = token_configurado()
        if not expected:
            raise AuthenticationFailed("Token de instrumento no configurado.")
        if not secrets.compare_digest(raw, expected):
            raise AuthenticationFailed("Token de instrumento inválido.")
        return (InstrumentGatewayUser(), "instrument-token")


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SPA/sesión para listados; el gateway usa InstrumentTokenAuthentication."""

    def enforce_csrf(self, request):
        return
