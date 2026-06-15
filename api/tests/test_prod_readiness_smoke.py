"""
PROD-6 — Readiness productivo controlado (tests estáticos / URLConf).

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.urls import resolve

REPO_ROOT = Path(__file__).resolve().parents[2]
READINESS_DOC = REPO_ROOT / 'docs_synesis' / 'PROD_READINESS_SMOKE.md'
SMOKE_SCRIPT = REPO_ROOT / 'deploy' / 'smoke' / 'prod_readiness_smoke.example.sh'
NGINX_CONF = REPO_ROOT / 'deploy' / 'nginx' / 'nginx.prod.example.conf'
URLS_PY = REPO_ROOT / 'api' / 'urls.py'
VIEWS_PY = REPO_ROOT / 'api' / 'views.py'

CRITICAL_ROUTE_FRAGMENTS = (
    'health/',
    'auth/login/',
    'auth/current-user/',
    'auth/logout/',
    'pacientes',
    'turnos',
    'atenciones',
    'lab/solicitudes',
    'laboratorio/solicitudes',
    'auditoria/',
    'registros-procedimientos',
    'registros-quirurgicos',
)


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def readiness_doc() -> str:
    return _read(READINESS_DOC)


@pytest.fixture(scope='module')
def smoke_script() -> str:
    return _read(SMOKE_SCRIPT)


class TestProdReadinessDocumentation:
    def test_readiness_smoke_md_existe(self):
        assert READINESS_DOC.is_file()

    def test_documenta_alcance_y_fuera_de_alcance(self, readiness_doc: str):
        lowered = readiness_doc.lower()
        assert 'alcance' in lowered
        assert 'fuera de alcance' in lowered
        assert 'datos sintéticos' in lowered or 'datos sinteticos' in lowered

    def test_documenta_go_nogo(self, readiness_doc: str):
        assert 'GO' in readiness_doc
        assert 'NO-GO' in readiness_doc

    def test_documenta_runbook_reversion(self, readiness_doc: str):
        assert 'reversión' in readiness_doc.lower() or 'reversion' in readiness_doc.lower()

    def test_documenta_matriz_roles(self, readiness_doc: str):
        for rol in ('admin', 'medico', 'paciente', 'laboratorio'):
            assert rol in readiness_doc.lower()

    def test_advierte_frontend_no_versionado(self, readiness_doc: str):
        assert 'frontend' in readiness_doc.lower()
        assert 'no hay frontend' in readiness_doc.lower() or 'no versionado' in readiness_doc.lower()

    def test_no_restore_real_obligatorio(self, readiness_doc: str):
        assert 'restore real' in readiness_doc.lower()
        assert 'no ejecutar restore' in readiness_doc.lower() or 'sin restore real' in readiness_doc.lower()

    def test_referencia_fases_cerradas(self, readiness_doc: str):
        for tag in ('PROD-3', 'PROD-4', 'PROD-5'):
            assert tag in readiness_doc


class TestProdReadinessSmokeScript:
    def test_smoke_script_existe(self):
        assert SMOKE_SCRIPT.is_file()

    def test_smoke_script_bash_n(self):
        import subprocess

        result = subprocess.run(
            ['bash', '-n', str(SMOKE_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_smoke_script_exige_base_url(self, smoke_script: str):
        assert 'BASE_URL' in smoke_script
        assert 'set -euo pipefail' in smoke_script

    def test_smoke_script_sin_credenciales_hardcodeadas(self, smoke_script: str):
        assert 'django-insecure' not in smoke_script.lower()
        assert 'REEMPLAZAR_CON_SECRETO' not in smoke_script
        assert re.search(r'password\s*=\s*["\'][^"\']{4,}["\']', smoke_script, re.I) is None

    def test_smoke_script_advierte_entorno_controlado(self, smoke_script: str):
        lowered = smoke_script.lower()
        assert 'controlado' in lowered or 'staging' in lowered or 'piloto' in lowered


class TestProdReadinessCriticalRoutes:
    def test_urls_py_registra_rutas_criticas(self):
        content = _read(URLS_PY)
        for fragment in CRITICAL_ROUTE_FRAGMENTS:
            assert fragment in content, fragment

    def test_health_endpoint_resuelve(self):
        match = resolve('/api/health/')
        assert match.url_name == 'health_check'

    def test_login_endpoint_resuelve(self):
        match = resolve('/api/auth/login/')
        assert match.url_name == 'login'

    def test_current_user_endpoint_resuelve(self):
        match = resolve('/api/auth/current-user/')
        assert match.url_name == 'current_user'


class TestProdReadinessMediaAndDownloads:
    def test_nginx_bloquea_media(self):
        content = _read(NGINX_CONF)
        media_block = content.split('location /media/', 1)[1].split('location', 1)[0]
        assert 'deny all' in media_block or 'return 404' in media_block

    def test_views_tiene_descargas_protegidas(self):
        content = _read(VIEWS_PY)
        assert 'download-adjunto-resultado' in content
        assert 'download-consentimiento-informado' in content
        assert '_clinical_file_download_response' in content

    def test_views_tiene_auditoria_descarga(self):
        content = _read(VIEWS_PY)
        assert '_audit_turnos_registro_download' in content
        assert 'registro_procedimiento_adjunto_download' in content

    def test_synesis_urls_media_solo_debug(self):
        urls_root = _read(REPO_ROOT / 'synesis' / 'urls.py')
        assert 'if settings.DEBUG:' in urls_root
        assert 'MEDIA_URL' in urls_root


class TestProdReadinessExistingTestSuite:
    @pytest.mark.parametrize(
        'rel_path',
        [
            'api/tests/test_prod_settings_security.py',
            'api/tests/test_prod_runtime_config.py',
            'api/tests/test_registro_adjuntos_download_prod4a.py',
            'api/tests/test_registro_adjuntos_download_audit_prod4b.py',
            'laboratorio/tests/test_lims_flujo_critico.py',
        ],
    )
    def test_archivo_test_readiness_referenciado_existe(self, rel_path: str):
        assert (REPO_ROOT / rel_path).is_file()

    def test_readiness_doc_referencia_tests_prod(self, readiness_doc: str):
        assert 'test_prod_readiness_smoke.py' in readiness_doc
        assert 'test_registro_adjuntos_download_prod4a.py' in readiness_doc
