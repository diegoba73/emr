"""
Helpers de configuración por entorno — PROD-1 / PROD-1-A.

Validaciones tempranas para producción sin romper desarrollo local (DEBUG=True por defecto).
"""
from __future__ import annotations

import os
import re
import string

from django.core.exceptions import ImproperlyConfigured

DEV_SECRET_PLACEHOLDER = (
    'django-insecure-az%_oz9f7vs-radm3ysub408scga8@g@1i7sr0)%*u&jvdlwk3'
)

# Placeholders exactos (comparación case-insensitive).
PLACEHOLDER_SECRET_KEYS = frozenset({
    '',
    'change-me',
    'changeme',
    'replace-me',
    'replace-this',
    'secret',
    'secret-key',
    'django-secret-key',
    'your-secret-key',
    'your-production-secret-key',
    'generate-a-long-random-secret-key',
    'generate-long-random-secret-key',
    'unsafe-secret-key',
    'insecure-secret-key',
    'dummy',
    'example',
    'placeholder',
    'dev_secret_key_change_me',
    DEV_SECRET_PLACEHOLDER,
})

# Frases documentales / instruccionales que no deben usarse como clave real.
PLACEHOLDER_PHRASE_SUBSTRINGS = (
    'generate-a-long-random-secret-key',
    'generate-long-random-secret-key',
    'your-secret-key',
    'your-production-secret-key',
    'reemplazar_con_secreto',
    'reemplazar-con-secreto',
    'no_commitear',
    'no-commitear',
)

OBVIOUS_PLACEHOLDER_TOKENS = frozenset({
    'change',
    'changeme',
    'replace',
    'replaceme',
    'placeholder',
    'example',
    'dummy',
    'insecure',
    'generate',
    'generated',
    'reemplazar',
    'commitear',
    'secret',
    'key',
    'long',
    'random',
    'unsafe',
    'production',
    'django',
})

PROD_SECRET_MIN_LENGTH = 50
PROD_SECRET_MIN_UNIQUE_CHARS = 12
PROD_SECRET_MIN_CHAR_CLASSES = 3

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

STRONG_SECRET_TEST_FIXTURE = (
    'Prod-Secret_2026__x9K!mQ#7vL@2pZ$rT%8nB&4yH*6sD?1fG+3wE'
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


def _normalize_secret_key(secret_key: str) -> str:
    return secret_key.strip().lower()


def _is_documented_placeholder(norm: str) -> bool:
    if norm in PLACEHOLDER_SECRET_KEYS:
        return True
    if any(phrase in norm for phrase in PLACEHOLDER_PHRASE_SUBSTRINGS):
        return True
    tokens = {t for t in re.split(r'[-_\s.+]+', norm) if t}
    if tokens and tokens <= OBVIOUS_PLACEHOLDER_TOKENS:
        return True
    return False


def _char_classes(secret_key: str) -> int:
    classes = 0
    if re.search(r'[a-z]', secret_key):
        classes += 1
    if re.search(r'[A-Z]', secret_key):
        classes += 1
    if re.search(r'\d', secret_key):
        classes += 1
    if re.search(r'[^A-Za-z0-9]', secret_key):
        classes += 1
    return classes


def _is_obvious_repeat_pattern(secret_key: str) -> bool:
    if not secret_key:
        return True
    if len(set(secret_key)) == 1:
        return True
    length = len(secret_key)
    for size in range(1, length // 2 + 1):
        if length % size == 0 and secret_key == secret_key[:size] * (length // size):
            return True
    return False


def validate_production_secret_key(secret_key: str) -> None:
    """
    Valida SECRET_KEY para DEBUG=False.

    No imprime ni registra el valor de la clave.
    """
    if not secret_key or not secret_key.strip():
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY debe definirse cuando DJANGO_DEBUG=False.'
        )

    stripped = secret_key.strip()
    norm = _normalize_secret_key(stripped)

    if stripped.startswith('django-insecure-'):
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY no puede usar el prefijo django-insecure- en producción.'
        )

    if _is_documented_placeholder(norm):
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY no puede ser un placeholder documentado en producción.'
        )

    if len(stripped) < PROD_SECRET_MIN_LENGTH:
        raise ImproperlyConfigured(
            f'DJANGO_SECRET_KEY debe tener al menos {PROD_SECRET_MIN_LENGTH} caracteres en producción.'
        )

    if len(set(stripped)) < PROD_SECRET_MIN_UNIQUE_CHARS:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY debe tener diversidad mínima de caracteres en producción.'
        )

    if _char_classes(stripped) < PROD_SECRET_MIN_CHAR_CLASSES:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY debe incluir al menos tres clases de caracteres '
            '(minúsculas, mayúsculas, dígitos o símbolos) en producción.'
        )

    if _is_obvious_repeat_pattern(stripped):
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY no puede ser una cadena repetitiva o de baja entropía en producción.'
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
