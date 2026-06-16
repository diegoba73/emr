"""
PROD-13 — Tests estáticos de hardening operativo sostenido.

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HARDENING_DOC = REPO_ROOT / 'docs_synesis' / 'PROD_OPERATIONAL_HARDENING.md'
ALERTS_TEMPLATE = REPO_ROOT / 'docs_synesis' / 'PROD_MONITORING_ALERTS_TEMPLATE.md'
ROTATION_RUNBOOK = REPO_ROOT / 'docs_synesis' / 'PROD_SECRET_ROTATION_RUNBOOK.md'
PROD_CHECKLIST = REPO_ROOT / 'docs_synesis' / 'PROD_CHECKLIST.md'
PROD_RUNTIME = REPO_ROOT / 'docs_synesis' / 'PROD_RUNTIME.md'
DOC_TESTS = REPO_ROOT / 'docs_synesis' / 'DOC_TESTS.md'

FORBIDDEN_IN_DOCS = [
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.I),
    re.compile(r'DATABASE_URL=postgres://[^:]+:[^@]+@'),
    re.compile(r'django-insecure-[a-z0-9]{20,}', re.I),
    re.compile(r'https?://[a-f0-9]{32}@[a-z0-9.-]+\.(sentry|datadog)', re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def hardening_doc() -> str:
    return _read(HARDENING_DOC)


@pytest.fixture(scope='module')
def alerts_template() -> str:
    return _read(ALERTS_TEMPLATE)


@pytest.fixture(scope='module')
def rotation_runbook() -> str:
    return _read(ROTATION_RUNBOOK)


class TestProdOperationalHardeningDocumentExists:
    def test_hardening_md_existe(self):
        assert HARDENING_DOC.is_file()

    def test_alerts_template_existe(self):
        assert ALERTS_TEMPLATE.is_file()

    def test_rotation_runbook_existe(self):
        assert ROTATION_RUNBOOK.is_file()

    def test_prod_checklist_referencia_prod13(self):
        content = _read(PROD_CHECKLIST)
        assert 'PROD-13' in content
        assert 'PROD_OPERATIONAL_HARDENING' in content

    def test_prod_runtime_referencia_prod13(self):
        content = _read(PROD_RUNTIME)
        assert 'PROD-13' in content

    def test_doc_tests_referencia_prod13(self):
        content = _read(DOC_TESTS)
        assert 'PROD-13' in content
        assert 'test_prod_operational_hardening.py' in content


class TestProdOperationalHardeningCore:
    def test_hardening_operativo_sostenido(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'hardening operativo sostenido' in lowered or 'hardening operativo' in lowered

    def test_monitoreo_externo(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'monitoreo externo' in lowered

    def test_apm(self, hardening_doc: str):
        assert 'APM' in hardening_doc

    def test_alertas(self, hardening_doc: str):
        assert 'alerta' in hardening_doc.lower()

    def test_sentry(self, hardening_doc: str):
        assert 'Sentry' in hardening_doc

    def test_datadog(self, hardening_doc: str):
        assert 'Datadog' in hardening_doc

    def test_prometheus(self, hardening_doc: str):
        assert 'Prometheus' in hardening_doc

    def test_grafana(self, hardening_doc: str):
        assert 'Grafana' in hardening_doc


class TestProdOperationalHardeningSignals:
    def test_healthcheck(self, hardening_doc: str):
        assert 'healthcheck' in hardening_doc.lower() or 'health' in hardening_doc.lower()

    def test_api_health(self, hardening_doc: str):
        assert '/api/health/' in hardening_doc

    def test_media(self, hardening_doc: str):
        assert '/media/' in hardening_doc

    def test_4xx(self, hardening_doc: str):
        assert '4xx' in hardening_doc

    def test_5xx(self, hardening_doc: str):
        assert '5xx' in hardening_doc

    def test_backend_caido(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'backend caído' in lowered or 'backend caido' in lowered

    def test_db_caida(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'db caída' in lowered or 'db caida' in lowered

    def test_proxy_caido(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'proxy caído' in lowered or 'proxy caido' in lowered or 'nginx/proxy' in lowered

    def test_nginx(self, hardening_doc: str):
        assert 'Nginx' in hardening_doc or 'nginx' in hardening_doc.lower()

    def test_postgresql(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'postgresql' in lowered or 'postgres' in lowered

    def test_contenedores(self, hardening_doc: str):
        assert 'contenedor' in hardening_doc.lower()

    def test_restarts(self, hardening_doc: str):
        assert 'restart' in hardening_doc.lower()

    def test_disco(self, hardening_doc: str):
        assert 'disco' in hardening_doc.lower()

    def test_backups_fallando(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'backup' in lowered and 'fall' in lowered

    def test_latencia(self, hardening_doc: str):
        assert 'latencia' in hardening_doc.lower()


class TestProdOperationalHardeningSecurity:
    def test_logs_sin_phi(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'log' in lowered and 'phi' in lowered

    def test_auditoria_critica(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'auditoría crítica' in lowered or 'auditoria critica' in lowered

    def test_rotacion_secretos(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'rotación de secretos' in lowered or 'rotacion de secretos' in lowered

    def test_secret_key(self, hardening_doc: str):
        assert 'SECRET_KEY' in hardening_doc

    def test_credenciales_db(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'credenciales' in lowered and ('db' in lowered or 'postgresql' in lowered)

    def test_tokens(self, hardening_doc: str):
        assert 'token' in hardening_doc.lower()

    def test_api_keys(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'api key' in lowered or 'api keys' in lowered

    def test_tls(self, hardening_doc: str):
        assert 'TLS' in hardening_doc

    def test_https(self, hardening_doc: str):
        assert 'HTTPS' in hardening_doc

    def test_x_forwarded_proto(self, hardening_doc: str):
        assert 'X-Forwarded-Proto' in hardening_doc

    def test_headers_seguridad(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'headers de seguridad' in lowered or 'header' in lowered

    def test_waf(self, hardening_doc: str):
        assert 'WAF' in hardening_doc

    def test_rate_limiting(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'rate limiting' in lowered or 'rate limit' in lowered

    def test_no_phi(self, hardening_doc: str):
        assert 'PHI' in hardening_doc

    def test_no_secretos(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'secreto' in lowered or 'dsn' in lowered or 'api key' in lowered


class TestProdOperationalHardeningGovernance:
    def test_evidencia_sanitizada(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'evidencia' in lowered and 'sanitiz' in lowered

    def test_fuera_del_repo(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'fuera del repo' in lowered

    def test_go_nogo(self, hardening_doc: str):
        assert 'GO' in hardening_doc
        assert 'NO-GO' in hardening_doc

    def test_frontend_no_versionado(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'frontend' in lowered
        assert 'no versionado' in lowered or 'no contiene' in lowered

    def test_validacion_frontend_separada(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'frontend' in lowered and 'separad' in lowered

    def test_produccion_clinica_abierta_fuera_alcance(self, hardening_doc: str):
        lowered = hardening_doc.lower()
        assert 'producción clínica abierta' in lowered or 'produccion clinica abierta' in lowered
        assert 'fuera de alcance' in lowered or 'no habilita' in lowered


class TestProdMonitoringAlertsTemplate:
    def test_nombre_alerta(self, alerts_template: str):
        lowered = alerts_template.lower()
        assert 'nombre de alerta' in lowered or 'nombre alerta' in lowered

    def test_severidad(self, alerts_template: str):
        assert 'Severidad' in alerts_template or 'severidad' in alerts_template.lower()

    def test_senal(self, alerts_template: str):
        assert 'Señal' in alerts_template or 'senal' in alerts_template.lower() or 'Señal' in alerts_template

    def test_umbral(self, alerts_template: str):
        assert 'Umbral' in alerts_template or 'umbral' in alerts_template.lower()

    def test_responsable(self, alerts_template: str):
        assert 'Responsable' in alerts_template or 'responsable' in alerts_template.lower()

    def test_canal_notificacion(self, alerts_template: str):
        lowered = alerts_template.lower()
        assert 'canal de notificación' in lowered or 'canal de notificacion' in lowered

    def test_accion_esperada(self, alerts_template: str):
        lowered = alerts_template.lower()
        assert 'acción esperada' in lowered or 'accion esperada' in lowered

    def test_evidencia_resolucion(self, alerts_template: str):
        lowered = alerts_template.lower()
        assert 'evidencia de resolución' in lowered or 'evidencia de resolucion' in lowered

    def test_template_no_phi(self, alerts_template: str):
        assert 'PHI' in alerts_template

    def test_template_no_secretos(self, alerts_template: str):
        lowered = alerts_template.lower()
        assert 'secreto' in lowered or 'dsn' in lowered or 'api key' in lowered


class TestProdSecretRotationRunbook:
    def test_inventario_secretos(self, rotation_runbook: str):
        lowered = rotation_runbook.lower()
        assert 'inventario de secretos' in lowered or 'inventario' in lowered

    def test_responsable(self, rotation_runbook: str):
        assert 'Responsable' in rotation_runbook or 'responsable' in rotation_runbook.lower()

    def test_periodicidad(self, rotation_runbook: str):
        assert 'Periodicidad' in rotation_runbook or 'periodicidad' in rotation_runbook.lower()

    def test_ventana_cambio(self, rotation_runbook: str):
        lowered = rotation_runbook.lower()
        assert 'ventana de cambio' in lowered or 'ventana' in lowered

    def test_rollback(self, rotation_runbook: str):
        assert 'rollback' in rotation_runbook.lower()

    def test_verificacion_post_rotacion(self, rotation_runbook: str):
        lowered = rotation_runbook.lower()
        assert 'verificación post-rotación' in lowered or 'verificacion post-rotacion' in lowered

    def test_prohibicion_valores_reales(self, rotation_runbook: str):
        lowered = rotation_runbook.lower()
        assert 'no exponer' in lowered or 'prohibición' in lowered or 'prohibicion' in lowered

    def test_evidencia_sanitizada_fuera_repo(self, rotation_runbook: str):
        lowered = rotation_runbook.lower()
        assert 'evidencia' in lowered and 'sanitiz' in lowered
        assert 'fuera del repo' in lowered


class TestProdOperationalHardeningDocumentSafety:
    @pytest.mark.parametrize('path', [HARDENING_DOC, ALERTS_TEMPLATE, ROTATION_RUNBOOK])
    def test_sin_patrones_secreto_en_docs(self, path: Path):
        content = _read(path)
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(content), f'{path.name}: {pattern.pattern}'
