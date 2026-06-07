"""
PROD-1 — tests de configuración mínima de producción.
"""
from __future__ import annotations

import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from synesis import env_config


class TestEnvConfigHelpers:
    def test_env_bool_truthy_values(self, monkeypatch):
        monkeypatch.setenv('TEST_FLAG', 'true')
        assert env_config.env_bool('TEST_FLAG') is True
        monkeypatch.setenv('TEST_FLAG', '1')
        assert env_config.env_bool('TEST_FLAG') is True

    def test_env_bool_default_when_unset(self, monkeypatch):
        monkeypatch.delenv('TEST_FLAG', raising=False)
        assert env_config.env_bool('TEST_FLAG', default=True) is True
        assert env_config.env_bool('TEST_FLAG', default=False) is False


class TestProductionSecretKey:
    def test_rejects_placeholder_in_production(self):
        with pytest.raises(ImproperlyConfigured):
            env_config.validate_production_secret_key('dev_secret_key_change_me')

    def test_rejects_django_insecure_prefix(self):
        with pytest.raises(ImproperlyConfigured):
            env_config.validate_production_secret_key('django-insecure-custom-key-here')

    def test_accepts_strong_key(self):
        env_config.validate_production_secret_key('a' * 64)


class TestProductionAllowedHosts:
    def test_rejects_wildcard(self):
        with pytest.raises(ImproperlyConfigured):
            env_config.validate_production_allowed_hosts(['*'])

    def test_resolve_dev_defaults_when_debug(self):
        hosts = env_config.resolve_allowed_hosts(debug=True)
        assert 'localhost' in hosts
        assert '*' not in hosts


class TestProductionCors:
    def test_cors_closed_requires_origins(self):
        with pytest.raises(ImproperlyConfigured):
            env_config.validate_production_cors(False, [])

    def test_resolve_cors_open_only_in_debug(self):
        allow_all, origins = env_config.resolve_cors(debug=True)
        assert allow_all is True
        assert origins

    def test_resolve_cors_closed_in_production(self, monkeypatch):
        monkeypatch.setenv(
            'DJANGO_CORS_ALLOWED_ORIGINS',
            'https://app.example.com',
        )
        allow_all, origins = env_config.resolve_cors(debug=False)
        assert allow_all is False
        assert 'https://app.example.com' in origins


class TestDrfRenderers:
    def test_browsable_api_only_in_debug(self):
        debug_renderers = env_config.resolve_drf_renderers(debug=True)
        prod_renderers = env_config.resolve_drf_renderers(debug=False)
        assert 'rest_framework.renderers.BrowsableAPIRenderer' in debug_renderers
        assert 'rest_framework.renderers.BrowsableAPIRenderer' not in prod_renderers
        assert prod_renderers == ['rest_framework.renderers.JSONRenderer']


class TestMediaUrls:
    def test_media_static_routes_only_when_debug(self):
        import synesis.urls as urls_module

        with override_settings(DEBUG=False, MEDIA_ROOT='/tmp/media', MEDIA_URL='/media/'):
            reloaded = importlib.reload(urls_module)
            media_patterns = [
                p
                for p in reloaded.urlpatterns
                if getattr(p, 'pattern', None) and 'media' in str(p.pattern)
            ]
            assert media_patterns == []

        with override_settings(DEBUG=True, MEDIA_ROOT='/tmp/media', MEDIA_URL='/media/'):
            reloaded = importlib.reload(urls_module)
            media_patterns = [
                p
                for p in reloaded.urlpatterns
                if getattr(p, 'pattern', None) and 'media' in str(p.pattern)
            ]
            assert media_patterns

        importlib.reload(urls_module)


class TestDevDefaultsWithoutEnv:
    """Defaults de desarrollo cuando DJANGO_DEBUG no está en entorno."""

    def test_debug_defaults_true_without_env(self, monkeypatch):
        monkeypatch.delenv('DJANGO_DEBUG', raising=False)
        assert env_config.resolve_debug() is True

    def test_browsable_api_enabled_when_debug(self):
        renderers = env_config.resolve_drf_renderers(debug=True)
        assert 'rest_framework.renderers.BrowsableAPIRenderer' in renderers

    def test_cors_allow_all_when_debug(self):
        allow_all, _ = env_config.resolve_cors(debug=True)
        assert allow_all is True


class TestProductionModeIntegration:
    """Arranque con flags de producción vía env (sin depender del .env local)."""

    def test_production_env_requires_strong_secret(self, monkeypatch):
        monkeypatch.setenv('DJANGO_DEBUG', 'false')
        monkeypatch.delenv('DJANGO_SECRET_KEY', raising=False)
        with pytest.raises(ImproperlyConfigured):
            env_config.resolve_secret_key(debug=False)

    def test_production_env_requires_csrf_origins(self, monkeypatch):
        monkeypatch.delenv('DJANGO_CSRF_TRUSTED_ORIGINS', raising=False)
        with pytest.raises(ImproperlyConfigured):
            env_config.resolve_csrf_trusted_origins(debug=False)
