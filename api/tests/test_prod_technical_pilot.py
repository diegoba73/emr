"""
PROD-10 — Tests estáticos del piloto técnico controlado.

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = REPO_ROOT / 'docs_synesis' / 'PROD_TECHNICAL_PILOT_RUNBOOK.md'
EVIDENCE_TEMPLATE = REPO_ROOT / 'docs_synesis' / 'PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md'
PILOT_SCRIPT = REPO_ROOT / 'deploy' / 'smoke' / 'prod_technical_pilot.example.sh'
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
    re.compile(r'echo\s+.*SMOKE_PASSWORD', re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def runbook() -> str:
    return _read(RUNBOOK)


@pytest.fixture(scope='module')
def evidence_template() -> str:
    return _read(EVIDENCE_TEMPLATE)


@pytest.fixture(scope='module')
def pilot_script() -> str:
    return _read(PILOT_SCRIPT)


class TestProdTechnicalPilotDocumentExists:
    def test_runbook_existe(self):
        assert RUNBOOK.is_file()

    def test_evidence_template_existe(self):
        assert EVIDENCE_TEMPLATE.is_file()

    def test_pilot_script_existe(self):
        assert PILOT_SCRIPT.is_file()

    def test_prod_checklist_referencia_prod10(self):
        content = _read(PROD_CHECKLIST)
        assert 'PROD-10' in content
        assert 'PROD_TECHNICAL_PILOT' in content

    def test_prod_runtime_referencia_prod10(self):
        content = _read(PROD_RUNTIME)
        assert 'PROD-10' in content

    def test_doc_tests_referencia_prod10(self):
        content = _read(DOC_TESTS)
        assert 'PROD-10' in content
        assert 'test_prod_technical_pilot.py' in content


class TestProdTechnicalPilotScope:
    def test_piloto_tecnico_controlado(self, runbook: str):
        lowered = runbook.lower()
        assert 'piloto técnico' in lowered or 'piloto tecnico' in lowered
        assert 'controlad' in lowered

    def test_referencia_prod8(self, runbook: str):
        assert 'PROD-8' in runbook
        assert 'PROD_PREPILOT' in runbook

    def test_referencia_prod9(self, runbook: str):
        assert 'PROD-9' in runbook
        assert 'PROD_OBSERVABILITY' in runbook

    def test_ventana_piloto(self, runbook: str):
        lowered = runbook.lower()
        assert 'ventana' in lowered and 'piloto' in lowered

    def test_responsable_operativo(self, runbook: str):
        lowered = runbook.lower()
        assert 'responsable operativo' in lowered or 'responsable' in lowered

    def test_commit_head(self, runbook: str):
        lowered = runbook.lower()
        assert 'commit' in lowered and 'head' in lowered


class TestProdTechnicalPilotSecurity:
    def test_debug_false(self, runbook: str):
        assert 'DEBUG=False' in runbook or 'DJANGO_DEBUG=False' in runbook

    def test_secret_key(self, runbook: str):
        assert 'SECRET_KEY' in runbook
        assert 'fuera del repo' in runbook.lower()

    def test_allowed_hosts(self, runbook: str):
        assert 'ALLOWED_HOSTS' in runbook

    def test_csrf_trusted_origins(self, runbook: str):
        assert 'CSRF_TRUSTED_ORIGINS' in runbook

    def test_cors(self, runbook: str):
        assert 'CORS' in runbook

    def test_tls_https(self, runbook: str):
        lowered = runbook.lower()
        assert 'tls' in lowered or 'https' in lowered

    def test_x_forwarded_proto(self, runbook: str):
        assert 'X-Forwarded-Proto' in runbook


class TestProdTechnicalPilotSmoke:
    def test_api_health(self, runbook: str):
        assert '/api/health/' in runbook

    def test_media_no_publico(self, runbook: str):
        assert '/media/' in runbook

    def test_apis_protegidas(self, runbook: str):
        lowered = runbook.lower()
        assert 'protegid' in lowered or '/api/pacientes/' in runbook

    def test_usuario_sintetico(self, runbook: str):
        lowered = runbook.lower()
        assert 'sintétic' in lowered or 'sintetic' in lowered


class TestProdTechnicalPilotOperations:
    def test_evidencia_sanitizada(self, runbook: str):
        lowered = runbook.lower()
        assert 'evidencia' in lowered
        assert 'sanitiz' in lowered or 'fuera del repo' in lowered

    def test_no_phi(self, runbook: str):
        assert 'PHI' in runbook

    def test_no_secretos(self, runbook: str):
        lowered = runbook.lower()
        assert 'secreto' in lowered or 'token' in lowered or 'password' in lowered

    def test_backups_programados(self, runbook: str):
        lowered = runbook.lower()
        assert 'backup' in lowered

    def test_restore_drill_prod7(self, runbook: str):
        assert 'PROD-7' in runbook

    def test_observabilidad(self, runbook: str):
        assert 'observabilidad' in runbook.lower()

    def test_logs(self, runbook: str):
        assert 'log' in runbook.lower()

    def test_errores_4xx(self, runbook: str):
        assert '4xx' in runbook

    def test_errores_5xx(self, runbook: str):
        assert '5xx' in runbook

    def test_go_nogo(self, runbook: str):
        assert 'GO' in runbook
        assert 'NO-GO' in runbook

    def test_rollback(self, runbook: str):
        assert 'rollback' in runbook.lower() or 'Rollback' in runbook

    def test_incidentes(self, runbook: str):
        assert 'incidente' in runbook.lower()


class TestProdTechnicalPilotScopeLimits:
    def test_frontend_no_versionado(self, runbook: str):
        lowered = runbook.lower()
        assert 'frontend' in lowered
        assert (
            'no versionado' in lowered
            or 'despliegue separado' in lowered
            or 'submódulo' in lowered
            or 'submodulo' in lowered
        )

    def test_produccion_clinica_abierta_fuera_alcance(self, runbook: str):
        lowered = runbook.lower()
        assert 'producción clínica abierta' in lowered or 'produccion clinica abierta' in lowered
        assert 'fuera de alcance' in lowered or 'no habilita' in lowered


class TestProdTechnicalPilotEvidenceTemplate:
    def test_template_fuera_del_repo(self, evidence_template: str):
        lowered = evidence_template.lower()
        assert 'fuera del repo' in lowered or 'fuera del repositorio' in lowered

    def test_template_sin_phi(self, evidence_template: str):
        assert 'PHI' in evidence_template

    def test_template_go_nogo(self, evidence_template: str):
        assert 'GO' in evidence_template
        assert 'NO-GO' in evidence_template

    def test_template_commit_head(self, evidence_template: str):
        lowered = evidence_template.lower()
        assert 'commit' in lowered


class TestProdTechnicalPilotScriptSafety:
    def test_script_bash_n(self):
        result = subprocess.run(
            ['bash', '-n', str(PILOT_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_script_set_euo_pipefail(self, pilot_script: str):
        assert 'set -euo pipefail' in pilot_script

    def test_script_exige_base_url(self, pilot_script: str):
        assert 'BASE_URL:?BASE_URL requerido' in pilot_script

    def test_script_sin_comandos_destructivos(self, pilot_script: str):
        for pattern in FORBIDDEN_IN_SCRIPT:
            assert not pattern.search(pilot_script), pattern.pattern

    def test_script_no_escribe_evidencia_en_repo(self, pilot_script: str):
        lowered = pilot_script.lower()
        assert 'fuera del repo' in lowered
        assert 'evidence_dir' in lowered or 'evidencia' in lowered

    def test_script_health_y_media(self, pilot_script: str):
        assert '/api/health/' in pilot_script
        assert '/media/' in pilot_script

    def test_script_login_y_current_user(self, pilot_script: str):
        assert '/api/auth/login/' in pilot_script
        assert '/api/auth/current-user/' in pilot_script


class TestProdTechnicalPilotDocumentSafety:
    @pytest.mark.parametrize('path', [RUNBOOK, EVIDENCE_TEMPLATE])
    def test_sin_patrones_secreto_en_docs(self, path: Path):
        content = _read(path)
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(content), f'{path.name}: {pattern.pattern}'
