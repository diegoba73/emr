"""
PROD-9 — Tests estáticos de observabilidad mínima.

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OBS_DOC = REPO_ROOT / 'docs_synesis' / 'PROD_OBSERVABILITY_MIN.md'
OBS_README = REPO_ROOT / 'deploy' / 'observability' / 'README.md'
OBS_SCRIPT = REPO_ROOT / 'deploy' / 'observability' / 'check_observability.example.sh'
PROD_CHECKLIST = REPO_ROOT / 'docs_synesis' / 'PROD_CHECKLIST.md'
PROD_RUNTIME = REPO_ROOT / 'docs_synesis' / 'PROD_RUNTIME.md'
DOC_TESTS = REPO_ROOT / 'docs_synesis' / 'DOC_TESTS.md'

FORBIDDEN_IN_DOCS = [
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.I),
    re.compile(r'DATABASE_URL=postgres://[^:]+:[^@]+@'),
    re.compile(r'django-insecure-[a-z0-9]{20,}', re.I),
]

FORBIDDEN_IN_SCRIPT = [
    re.compile(r'\brm\s+-rf\b'),
    re.compile(r'\bdropdb\b', re.I),
    re.compile(r'docker\s+compose\s+down\s+.*-v'),
    re.compile(r'\bpg_restore\b'),
    re.compile(r'echo\s+.*PGPASSWORD', re.I),
    re.compile(r'echo\s+.*SECRET_KEY', re.I),
    re.compile(r'echo\s+.*TOKEN', re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def obs_doc() -> str:
    return _read(OBS_DOC)


@pytest.fixture(scope='module')
def obs_script() -> str:
    return _read(OBS_SCRIPT)


class TestProdObservabilityDocumentExists:
    def test_observability_min_md_existe(self):
        assert OBS_DOC.is_file()

    def test_observability_readme_existe(self):
        assert OBS_README.is_file()

    def test_check_script_existe(self):
        assert OBS_SCRIPT.is_file()

    def test_prod_checklist_referencia_prod9(self):
        content = _read(PROD_CHECKLIST)
        assert 'PROD-9' in content
        assert 'PROD_OBSERVABILITY_MIN' in content

    def test_prod_runtime_referencia_prod9(self):
        content = _read(PROD_RUNTIME)
        assert 'PROD-9' in content

    def test_doc_tests_referencia_prod9(self):
        content = _read(DOC_TESTS)
        assert 'PROD-9' in content
        assert 'test_prod_observability_min.py' in content


class TestProdObservabilityLogs:
    def test_logs_backend_gunicorn(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'gunicorn' in lowered
        assert 'backend' in lowered or 'logs backend' in lowered

    def test_logs_nginx(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'nginx' in lowered
        assert 'log' in lowered

    def test_logs_postgresql(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'postgresql' in lowered or 'postgres' in lowered
        assert 'log' in lowered


class TestProdObservabilityErrorsAndHealth:
    def test_errores_4xx(self, obs_doc: str):
        assert '4xx' in obs_doc

    def test_errores_5xx(self, obs_doc: str):
        assert '5xx' in obs_doc

    def test_healthcheck(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'healthcheck' in lowered or 'health check' in lowered

    def test_api_health_endpoint(self, obs_doc: str):
        assert '/api/health/' in obs_doc

    def test_media_no_publico(self, obs_doc: str):
        assert '/media/' in obs_doc


class TestProdObservabilityInfrastructure:
    def test_contenedores(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'contenedor' in lowered or 'docker' in lowered

    def test_postgresql_monitoreo(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'postgresql' in lowered or 'postgres' in lowered
        assert 'pg_isready' in lowered or 'pg_database_size' in lowered

    def test_espacio_disco(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'disco' in lowered or 'df -h' in lowered

    def test_backups_programados(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'backup' in lowered

    def test_restore_drill_prod7(self, obs_doc: str):
        assert 'PROD-7' in obs_doc
        lowered = obs_doc.lower()
        assert 'restore drill' in lowered or 'restore_drill' in lowered


class TestProdObservabilityIncidents:
    def test_responsable_operativo(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'responsable operativo' in lowered or 'responsable' in lowered

    def test_incidentes(self, obs_doc: str):
        assert 'incidente' in obs_doc.lower()

    def test_backend_caido(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'backend' in lowered and ('caíd' in lowered or 'caid' in lowered or 'caída' in lowered)

    def test_db_caida(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert ('db' in lowered or 'base de datos' in lowered) and (
            'caíd' in lowered or 'caid' in lowered or 'caída' in lowered
        )

    def test_proxy_caido(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'nginx' in lowered or 'proxy' in lowered

    def test_media_privada(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'media' in lowered and 'privad' in lowered

    def test_disco_lleno(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'disco' in lowered and ('lleno' in lowered or 'llen' in lowered)

    def test_backups_fallando(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'backup' in lowered and 'fall' in lowered

    def test_sospecha_phi(self, obs_doc: str):
        assert 'PHI' in obs_doc
        lowered = obs_doc.lower()
        assert 'sospecha' in lowered or 'exposición' in lowered or 'exposicion' in lowered


class TestProdObservabilityGovernance:
    def test_go_nogo(self, obs_doc: str):
        assert 'GO' in obs_doc
        assert 'NO-GO' in obs_doc

    def test_evidencia_sanitizada(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'evidencia' in lowered
        assert 'sanitiz' in lowered or 'fuera del repo' in lowered

    def test_no_phi(self, obs_doc: str):
        assert 'PHI' in obs_doc

    def test_no_secretos(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'secreto' in lowered or 'secretos' in lowered or 'token' in lowered

    def test_frontend_no_versionado(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'frontend' in lowered
        assert (
            'no versionado' in lowered
            or 'despliegue separado' in lowered
            or 'submódulo' in lowered
            or 'submodulo' in lowered
        )

    def test_produccion_clinica_abierta_fuera_alcance(self, obs_doc: str):
        lowered = obs_doc.lower()
        assert 'producción clínica abierta' in lowered or 'produccion clinica abierta' in lowered
        assert 'fuera de alcance' in lowered


class TestProdObservabilityScriptSafety:
    def test_script_bash_n(self):
        result = subprocess.run(
            ['bash', '-n', str(OBS_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_script_set_euo_pipefail(self, obs_script: str):
        assert 'set -euo pipefail' in obs_script

    def test_script_exige_base_url(self, obs_script: str):
        assert 'BASE_URL:?BASE_URL requerido' in obs_script

    def test_script_sin_comandos_destructivos(self, obs_script: str):
        for pattern in FORBIDDEN_IN_SCRIPT:
            assert not pattern.search(obs_script), pattern.pattern

    def test_script_menciona_health_y_media(self, obs_script: str):
        assert '/api/health/' in obs_script
        assert '/media/' in obs_script

    def test_script_menciona_pacientes_anonimo(self, obs_script: str):
        assert '/api/pacientes/' in obs_script


class TestProdObservabilityDocumentSafety:
    @pytest.mark.parametrize('path', [OBS_DOC, PROD_CHECKLIST])
    def test_sin_patrones_secreto_en_docs(self, path: Path):
        content = _read(path)
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(content), f'{path.name}: {pattern.pattern}'
