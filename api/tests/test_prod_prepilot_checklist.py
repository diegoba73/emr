"""
PROD-8 — Tests estáticos del checklist pre-piloto productivo.

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PREPILOT_DOC = REPO_ROOT / 'docs_synesis' / 'PROD_PREPILOT_CHECKLIST.md'
PROD_CHECKLIST = REPO_ROOT / 'docs_synesis' / 'PROD_CHECKLIST.md'
PROD_RUNTIME = REPO_ROOT / 'docs_synesis' / 'PROD_RUNTIME.md'
DOC_TESTS = REPO_ROOT / 'docs_synesis' / 'DOC_TESTS.md'

FORBIDDEN_IN_DOCS = [
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.I),
    re.compile(r'DATABASE_URL=postgres://[^:]+:[^@]+@'),
    re.compile(r'django-insecure-[a-z0-9]{20,}', re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def prepilot_doc() -> str:
    return _read(PREPILOT_DOC)


class TestProdPrepilotDocumentExists:
    def test_prepilot_checklist_md_existe(self):
        assert PREPILOT_DOC.is_file()

    def test_prod_checklist_referencia_prod8(self):
        content = _read(PROD_CHECKLIST)
        assert 'PROD-8' in content
        assert 'PROD_PREPILOT_CHECKLIST' in content

    def test_prod_runtime_referencia_prod8(self):
        content = _read(PROD_RUNTIME)
        assert 'PROD-8' in content

    def test_doc_tests_referencia_prod8(self):
        content = _read(DOC_TESTS)
        assert 'PROD-8' in content
        assert 'test_prod_prepilot_checklist.py' in content


class TestProdPrepilotSecurityPreconditions:
    def test_exige_debug_false(self, prepilot_doc: str):
        assert 'DEBUG=False' in prepilot_doc or 'DJANGO_DEBUG=False' in prepilot_doc

    def test_menciona_secret_key(self, prepilot_doc: str):
        assert 'SECRET_KEY' in prepilot_doc
        assert 'fuera del repo' in prepilot_doc.lower()

    def test_menciona_allowed_hosts(self, prepilot_doc: str):
        assert 'ALLOWED_HOSTS' in prepilot_doc

    def test_menciona_csrf_trusted_origins(self, prepilot_doc: str):
        assert 'CSRF_TRUSTED_ORIGINS' in prepilot_doc

    def test_menciona_cors_cerrado(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'cors' in lowered
        assert 'cerrado' in lowered or 'cerrada' in lowered

    def test_menciona_tls_https(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'tls' in lowered or 'https' in lowered

    def test_menciona_x_forwarded_proto(self, prepilot_doc: str):
        assert 'X-Forwarded-Proto' in prepilot_doc

    def test_media_no_publica(self, prepilot_doc: str):
        assert '/media/' in prepilot_doc
        lowered = prepilot_doc.lower()
        assert 'no' in lowered and ('públic' in lowered or 'public' in lowered or 'expuesto' in lowered)


class TestProdPrepilotOperations:
    def test_menciona_backups(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'backup' in lowered

    def test_menciona_restore_drill(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'restore drill' in lowered or 'restore_drill' in lowered or 'produ-7' in lowered

    def test_menciona_monitoreo(self, prepilot_doc: str):
        assert 'monitoreo' in prepilot_doc.lower()

    def test_menciona_rollback(self, prepilot_doc: str):
        assert 'rollback' in prepilot_doc.lower() or 'Rollback' in prepilot_doc

    def test_documenta_go_nogo(self, prepilot_doc: str):
        assert 'GO' in prepilot_doc
        assert 'NO-GO' in prepilot_doc


class TestProdPrepilotUsersAndData:
    def test_usuarios_internos_autorizados(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'usuarios internos' in lowered or 'internos autorizados' in lowered

    def test_menciona_roles(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'rol' in lowered or 'roles' in lowered
        assert 'laboratorio' in lowered

    def test_datos_sinteticos(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'sintétic' in lowered or 'sintetic' in lowered

    def test_autorizacion_formal_datos_reales(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'autorización formal' in lowered or 'autorizacion formal' in lowered


class TestProdPrepilotScopeLimits:
    def test_frontend_validacion_separada(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'frontend' in lowered
        assert (
            'no versionado' in lowered
            or 'repositorio' in lowered
            or 'despliegue separado' in lowered
            or 'submódulo' in lowered
            or 'submodulo' in lowered
        )

    def test_produccion_clinica_abierta_fuera_alcance(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'producción clínica abierta' in lowered or 'produccion clinica abierta' in lowered
        assert 'fuera de alcance' in lowered or 'no habilita' in lowered

    def test_evidencia_sanitizada(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'evidencia' in lowered
        assert 'sanitiz' in lowered or 'fuera del repo' in lowered

    def test_no_phi(self, prepilot_doc: str):
        assert 'PHI' in prepilot_doc
        lowered = prepilot_doc.lower()
        assert 'no' in lowered

    def test_no_secretos(self, prepilot_doc: str):
        lowered = prepilot_doc.lower()
        assert 'secreto' in lowered or 'secretos' in lowered or 'password' in lowered


class TestProdPrepilotDocumentSafety:
    @pytest.mark.parametrize('path', [PREPILOT_DOC, PROD_CHECKLIST])
    def test_sin_patrones_secreto_en_docs(self, path: Path):
        content = _read(path)
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(content), f'{path.name}: {pattern.pattern}'


class TestProdPrepilotReferences:
    def test_referencia_readiness_smoke(self, prepilot_doc: str):
        assert 'PROD_READINESS_SMOKE' in prepilot_doc or 'prod_readiness_smoke' in prepilot_doc

    def test_referencia_endpoints_verificacion(self, prepilot_doc: str):
        assert '/api/health/' in prepilot_doc
        assert '/api/auth/login/' in prepilot_doc

    def test_referencia_descargas_protegidas(self, prepilot_doc: str):
        assert 'download-adjunto-resultado' in prepilot_doc
        assert 'download-consentimiento-informado' in prepilot_doc
