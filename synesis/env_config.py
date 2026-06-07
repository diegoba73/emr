"""
Helpers de configuración por entorno — PROD-1.

Validaciones tempranas para producción sin romper desarrollo local (DEBUG=True por defecto).
"""
from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

DEV_SECRET_PLACEHOLDER = (
    'django-insecure-az%_oz9f7vs-radm3ysub408scga8@g@1i7sr0)%*u&jvdlwk3'
)

INSECURE_SECRET_KEYS = frozenset({
    '',
    'change-me',
    'dev_secret_key_change_me',
    DEV_SECRET_PLACEHOLDER,
})

DEV_ALLOWED_HOSTS = ('localhost', '127.0.0.1', '0.0.0.0')

DEV_CORS_ORIGINS = (
    'http://localhost:3000',
    'http://127.0.0.1:3000',
)

DEV_CSRF_ORIGINS = (
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def parse_csv_env(name: str, default: tuple[str, ...] | list[str] | None = None) -> list[str]:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        if default is None:
            return []
        return list(default)
    return [part.strip() for part in str(raw).split(',') if part.strip()]


def resolve_debug() -> bool:
    """DEBUG por env; default True para desarrollo local."""
    return env_bool('DJANGO_DEBUG', default=True)


def resolve_secret_key(debug: bool) -> str:
    key = os.getenv('DJANGO_SECRET_KEY', DEV_SECRET_PLACEHOLDER)
    if not debug:
        validate_production_secret_key(key)
    return key


def validate_production_secret_key(secret_key: str) -> None:
    if not secret_key or secret_key.strip() in INSECURE_SECRET_KEYS:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY debe definirse con un valor seguro cuando DJANGO_DEBUG=False.'
        )
    if secret_key.startswith('django-insecure-'):
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY no puede usar el prefijo django-insecure- en producción.'
        )


def resolve_allowed_hosts(debug: bool) -> list[str]:
    hosts = parse_csv_env('DJANGO_ALLOWED_HOSTS')
    if debug:
        return hosts if hosts else list(DEV_ALLOWED_HOSTS)
    if not hosts:
        raise ImproperlyConfigured(
            'DJANGO_ALLOWED_HOSTS debe definirse cuando DJANGO_DEBUG=False.'
        )
    validate_production_allowed_hosts(hosts)
    return hosts


def validate_production_allowed_hosts(allowed_hosts: list[str]) -> None:
    if '*' in allowed_hosts:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS no puede contener '*' en producción."
        )


def resolve_cors(debug: bool) -> tuple[bool, list[str]]:
    if debug:
        origins = parse_csv_env('DJANGO_CORS_ALLOWED_ORIGINS', default=DEV_CORS_ORIGINS)
        return True, origins
    if env_bool('DJANGO_CORS_ALLOW_ALL_ORIGINS', default=False):
        raise ImproperlyConfigured(
            'DJANGO_CORS_ALLOW_ALL_ORIGINS no está permitido cuando DJANGO_DEBUG=False.'
        )
    origins = parse_csv_env('DJANGO_CORS_ALLOWED_ORIGINS')
    validate_production_cors(False, origins)
    return False, origins


def validate_production_cors(cors_allow_all: bool, cors_allowed_origins: list[str]) -> None:
    if cors_allow_all:
        raise ImproperlyConfigured(
            'CORS abierto no está permitido cuando DJANGO_DEBUG=False.'
        )
    if not cors_allowed_origins:
        raise ImproperlyConfigured(
            'DJANGO_CORS_ALLOWED_ORIGINS debe definirse cuando DJANGO_DEBUG=False.'
        )


def resolve_csrf_trusted_origins(debug: bool) -> list[str]:
    origins = parse_csv_env('DJANGO_CSRF_TRUSTED_ORIGINS')
    if debug:
        return origins if origins else list(DEV_CSRF_ORIGINS)
    if not origins:
        raise ImproperlyConfigured(
            'DJANGO_CSRF_TRUSTED_ORIGINS debe definirse cuando DJANGO_DEBUG=False.'
        )
    return origins


def resolve_drf_renderers(debug: bool) -> list[str]:
    if debug:
        return [
            'rest_framework.renderers.JSONRenderer',
            'rest_framework.renderers.BrowsableAPIRenderer',
        ]
    return ['rest_framework.renderers.JSONRenderer']
