"""
PROD-2-A — tests de configuración de runtime productivo (lectura de archivos).
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding='utf-8')


class TestEntrypointRuntime:
    def test_entrypoint_contiene_rama_runserver(self):
        content = _read('entrypoint.sh')
        assert 'runserver' in content
        assert 'DJANGO_RUNTIME' in content

    def test_entrypoint_contiene_rama_gunicorn(self):
        content = _read('entrypoint.sh')
        assert 'gunicorn synesis.wsgi:application' in content

    def test_entrypoint_rechaza_runtime_invalido(self):
        content = _read('entrypoint.sh')
        assert 'DJANGO_RUNTIME inválido' in content


class TestDockerComposeDev:
    def test_docker_compose_dev_usa_runserver(self):
        content = _read('docker-compose.yml')
        assert 'DJANGO_RUNTIME: "runserver"' in content
        assert 'DJANGO_DEBUG: "true"' in content


class TestDockerComposeProdExample:
    def test_prod_example_usa_gunicorn(self):
        content = _read('docker-compose.prod.example.yml')
        assert 'DJANGO_RUNTIME: "gunicorn"' in content
        assert 'DJANGO_DEBUG: "False"' in content

    def test_prod_example_no_contiene_secretos_reales(self):
        content = _read('docker-compose.prod.example.yml')
        lowered = content.lower()
        assert 'django-insecure' not in lowered
        assert 'generate-a-long-random-secret-key' not in lowered
        assert '${DJANGO_SECRET_KEY' in content


class TestEnvExamples:
    def test_env_production_example_usa_gunicorn(self):
        content = _read('.env.production.example')
        assert 'DJANGO_RUNTIME=gunicorn' in content

    def test_env_example_dev_usa_runserver(self):
        content = _read('.env.example')
        assert 'DJANGO_RUNTIME=runserver' in content


class TestRequirements:
    def test_requirements_incluye_gunicorn(self):
        content = _read('requirements.txt')
        assert 'gunicorn' in content.lower()


@pytest.mark.parametrize(
    'rel_path',
    [
        'docs_synesis/PROD_RUNTIME.md',
    ],
)
def test_doc_runtime_existe(rel_path: str):
    assert (REPO_ROOT / rel_path).is_file()
