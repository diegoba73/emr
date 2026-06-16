"""
PROD-11 — Tests estáticos de revisión post-piloto.

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = REPO_ROOT / 'docs_synesis' / 'PROD_POST_PILOT_REVIEW.md'
ACTIONS_TEMPLATE = REPO_ROOT / 'docs_synesis' / 'PROD_POST_PILOT_ACTIONS_TEMPLATE.md'
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
def review_doc() -> str:
    return _read(REVIEW_DOC)


@pytest.fixture(scope='module')
def actions_template() -> str:
    return _read(ACTIONS_TEMPLATE)


class TestProdPostPilotDocumentExists:
    def test_post_pilot_review_md_existe(self):
        assert REVIEW_DOC.is_file()

    def test_actions_template_existe(self):
        assert ACTIONS_TEMPLATE.is_file()

    def test_prod_checklist_referencia_prod11(self):
        content = _read(PROD_CHECKLIST)
        assert 'PROD-11' in content
        assert 'PROD_POST_PILOT' in content

    def test_prod_runtime_referencia_prod11(self):
        content = _read(PROD_RUNTIME)
        assert 'PROD-11' in content

    def test_doc_tests_referencia_prod11(self):
        content = _read(DOC_TESTS)
        assert 'PROD-11' in content
        assert 'test_prod_post_pilot_review.py' in content


class TestProdPostPilotScope:
    def test_revision_post_piloto(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'post-piloto' in lowered or 'post piloto' in lowered
        assert 'revisión' in lowered or 'revision' in lowered

    def test_piloto_tecnico_controlado(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'piloto técnico' in lowered or 'piloto tecnico' in lowered

    def test_referencia_prod8(self, review_doc: str):
        assert 'PROD-8' in review_doc

    def test_referencia_prod9(self, review_doc: str):
        assert 'PROD-9' in review_doc

    def test_referencia_prod10(self, review_doc: str):
        assert 'PROD-10' in review_doc


class TestProdPostPilotEvidence:
    def test_evidencia_sanitizada(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'evidencia' in lowered
        assert 'sanitiz' in lowered

    def test_evidencia_fuera_del_repo(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'fuera del repo' in lowered

    def test_go_nogo(self, review_doc: str):
        assert 'GO' in review_doc
        assert 'NO-GO' in review_doc

    def test_commit_head(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'commit' in lowered and 'head' in lowered

    def test_ventana_piloto(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'ventana' in lowered and 'piloto' in lowered

    def test_responsable_operativo(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'responsable operativo' in lowered or 'responsable' in lowered


class TestProdPostPilotSmokeReview:
    def test_api_health(self, review_doc: str):
        assert '/api/health/' in review_doc

    def test_media(self, review_doc: str):
        assert '/media/' in review_doc

    def test_apis_protegidas(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'protegid' in lowered or '/api/pacientes/' in review_doc

    def test_usuario_sintetico(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'sintétic' in lowered or 'sintetic' in lowered

    def test_login(self, review_doc: str):
        assert '/api/auth/login/' in review_doc

    def test_current_user(self, review_doc: str):
        assert 'current-user' in review_doc


class TestProdPostPilotObservabilityReview:
    def test_logs_backend(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'backend' in lowered and 'log' in lowered

    def test_logs_gunicorn(self, review_doc: str):
        assert 'Gunicorn' in review_doc or 'gunicorn' in review_doc.lower()

    def test_logs_nginx(self, review_doc: str):
        assert 'Nginx' in review_doc or 'nginx' in review_doc.lower()

    def test_logs_postgresql(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'postgresql' in lowered or 'postgres' in lowered

    def test_errores_4xx(self, review_doc: str):
        assert '4xx' in review_doc

    def test_errores_5xx(self, review_doc: str):
        assert '5xx' in review_doc

    def test_contenedores(self, review_doc: str):
        assert 'contenedor' in review_doc.lower()

    def test_health(self, review_doc: str):
        assert 'health' in review_doc.lower()

    def test_restarts(self, review_doc: str):
        assert 'restart' in review_doc.lower()

    def test_postgresql(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'postgresql' in lowered or 'postgres' in lowered

    def test_espacio_disco(self, review_doc: str):
        assert 'disco' in review_doc.lower()

    def test_backups_programados(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'backup' in lowered

    def test_restore_drill_prod7(self, review_doc: str):
        assert 'PROD-7' in review_doc


class TestProdPostPilotGovernance:
    def test_incidentes(self, review_doc: str):
        assert 'incidente' in review_doc.lower()

    def test_sospecha_phi(self, review_doc: str):
        assert 'PHI' in review_doc
        lowered = review_doc.lower()
        assert 'sospecha' in lowered or 'expuesta' in lowered or 'expuesto' in lowered

    def test_no_phi(self, review_doc: str):
        assert 'PHI' in review_doc

    def test_no_secretos(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'secreto' in lowered or 'token' in lowered or 'password' in lowered

    def test_acciones_correctivas(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'acciones correctivas' in lowered or 'acción correctiva' in lowered

    def test_riesgos_residuales(self, review_doc: str):
        assert 'riesgos residuales' in review_doc.lower() or 'riesgo residual' in review_doc.lower()

    def test_autorizacion_institucional(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'autorización institucional' in lowered or 'autorizacion institucional' in lowered

    def test_datos_reales_minimos(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'datos reales' in lowered


class TestProdPostPilotFrontendScope:
    def test_frontend_no_versionado(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'frontend' in lowered
        assert (
            'no versionado' in lowered
            or 'despliegue separado' in lowered
            or 'submódulo' in lowered
            or 'submodulo' in lowered
        )

    def test_validacion_frontend_separada(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'frontend' in lowered and 'separad' in lowered

    def test_produccion_clinica_abierta_fuera_alcance(self, review_doc: str):
        lowered = review_doc.lower()
        assert 'producción clínica abierta' in lowered or 'produccion clinica abierta' in lowered
        assert 'fuera de alcance' in lowered or 'no habilita' in lowered


class TestProdPostPilotActionsTemplate:
    def test_identificador_accion(self, actions_template: str):
        assert 'ACT-' in actions_template or 'ID' in actions_template

    def test_severidad(self, actions_template: str):
        assert 'Severidad' in actions_template or 'severidad' in actions_template.lower()

    def test_responsable(self, actions_template: str):
        assert 'Responsable' in actions_template or 'responsable' in actions_template.lower()

    def test_fecha_objetivo(self, actions_template: str):
        lowered = actions_template.lower()
        assert 'fecha objetivo' in lowered or 'fecha cierre' in lowered

    def test_evidencia_cierre(self, actions_template: str):
        lowered = actions_template.lower()
        assert 'evidencia de cierre' in lowered or 'evidencia' in lowered

    def test_impacto(self, actions_template: str):
        assert 'Impacto' in actions_template or 'impacto' in actions_template.lower()

    def test_decision(self, actions_template: str):
        assert 'Decisión' in actions_template or 'decision' in actions_template.lower()

    def test_bloqueo_go(self, actions_template: str):
        lowered = actions_template.lower()
        assert 'bloquea go' in lowered or 'bloquea' in lowered

    def test_template_no_phi(self, actions_template: str):
        assert 'PHI' in actions_template

    def test_template_no_secretos(self, actions_template: str):
        lowered = actions_template.lower()
        assert 'secreto' in lowered or 'token' in lowered or 'password' in lowered

    def test_template_fuera_del_repo(self, actions_template: str):
        lowered = actions_template.lower()
        assert 'fuera del repo' in lowered or 'fuera del repositorio' in lowered


class TestProdPostPilotDocumentSafety:
    @pytest.mark.parametrize('path', [REVIEW_DOC, ACTIONS_TEMPLATE])
    def test_sin_patrones_secreto_en_docs(self, path: Path):
        content = _read(path)
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(content), f'{path.name}: {pattern.pattern}'
