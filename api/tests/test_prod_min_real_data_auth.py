"""
PROD-12 — Tests estáticos de autorización institucional y piloto datos reales mínimos.

No contacta producción real ni servicios externos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = REPO_ROOT / 'docs_synesis' / 'PROD_MIN_REAL_DATA_AUTH.md'
SCOPE_TEMPLATE = REPO_ROOT / 'docs_synesis' / 'PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md'
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
def auth_doc() -> str:
    return _read(AUTH_DOC)


@pytest.fixture(scope='module')
def scope_template() -> str:
    return _read(SCOPE_TEMPLATE)


class TestProdMinRealDataDocumentExists:
    def test_auth_md_existe(self):
        assert AUTH_DOC.is_file()

    def test_scope_template_existe(self):
        assert SCOPE_TEMPLATE.is_file()

    def test_prod_checklist_referencia_prod12(self):
        content = _read(PROD_CHECKLIST)
        assert 'PROD-12' in content
        assert 'PROD_MIN_REAL_DATA' in content

    def test_prod_runtime_referencia_prod12(self):
        content = _read(PROD_RUNTIME)
        assert 'PROD-12' in content

    def test_doc_tests_referencia_prod12(self):
        content = _read(DOC_TESTS)
        assert 'PROD-12' in content
        assert 'test_prod_min_real_data_auth.py' in content


class TestProdMinRealDataCoreConcepts:
    def test_autorizacion_institucional(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'autorización institucional' in lowered or 'autorizacion institucional' in lowered

    def test_piloto_datos_reales_minimos(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'datos reales' in lowered and 'mínim' in lowered or 'minim' in lowered

    def test_go_post_piloto_prod11(self, auth_doc: str):
        assert 'PROD-11' in auth_doc
        lowered = auth_doc.lower()
        assert 'post-piloto' in lowered or 'post piloto' in lowered

    def test_evidencia_externa(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'evidencia' in lowered and 'extern' in lowered

    def test_evidencia_sanitizada(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'sanitiz' in lowered


class TestProdMinRealDataActionsAndResponsibles:
    def test_acciones_criticas_cerradas(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'acciones críticas' in lowered or 'acciones criticas' in lowered
        assert 'cerrad' in lowered

    def test_responsable_institucional(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'responsable institucional' in lowered

    def test_responsable_clinico(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'responsable clínico' in lowered or 'responsable clinico' in lowered

    def test_responsable_tecnico(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'responsable técnico' in lowered or 'responsable tecnico' in lowered


class TestProdMinRealDataScope:
    def test_alcance_funcional_limitado(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'alcance funcional limitado' in lowered or 'alcance funcional' in lowered

    def test_modulos_habilitados(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'módulos habilitados' in lowered or 'modulos habilitados' in lowered

    def test_modulos_excluidos(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'módulos excluidos' in lowered or 'modulos excluidos' in lowered

    def test_roles_habilitados(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'roles habilitados' in lowered or 'roles y usuarios' in lowered

    def test_usuarios_nominales(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'usuarios nominales' in lowered or 'usuarios internos' in lowered

    def test_datos_reales_minimos(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'datos reales mínimos' in lowered or 'datos reales minimos' in lowered

    def test_datos_prohibidos(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'datos prohibidos' in lowered

    def test_ventana_limitada(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'ventana' in lowered


class TestProdMinRealDataOperations:
    def test_suspension_inmediata(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'suspensión inmediata' in lowered or 'suspension inmediata' in lowered

    def test_incidente(self, auth_doc: str):
        assert 'incidente' in auth_doc.lower()

    def test_rollback(self, auth_doc: str):
        assert 'rollback' in auth_doc.lower()


class TestProdMinRealDataInfrastructure:
    def test_backups_programados(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'backup' in lowered

    def test_restore_drill_prod7(self, auth_doc: str):
        assert 'PROD-7' in auth_doc

    def test_observabilidad_prod9(self, auth_doc: str):
        assert 'PROD-9' in auth_doc

    def test_revision_post_piloto_prod11(self, auth_doc: str):
        assert 'PROD-11' in auth_doc
        lowered = auth_doc.lower()
        assert 'post-piloto' in lowered or 'post piloto' in lowered


class TestProdMinRealDataSecurity:
    def test_media(self, auth_doc: str):
        assert '/media/' in auth_doc

    def test_apis_protegidas(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'apis protegidas' in lowered or 'protegid' in lowered

    def test_no_phi(self, auth_doc: str):
        assert 'PHI' in auth_doc

    def test_no_secretos(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'secreto' in lowered or 'token' in lowered or 'password' in lowered

    def test_no_actas_reales_en_repo(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'actas reales' in lowered or 'acta real' in lowered
        assert 'repo' in lowered

    def test_no_autorizaciones_reales_en_repo(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'autorizaciones' in lowered or 'autorización' in lowered
        assert 'repo' in lowered


class TestProdMinRealDataFrontend:
    def test_frontend_no_versionado(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'frontend' in lowered
        assert 'no versionado' in lowered or 'no contiene' in lowered

    def test_validacion_frontend_separada(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'frontend' in lowered and 'separad' in lowered

    def test_produccion_clinica_abierta_fuera_alcance(self, auth_doc: str):
        lowered = auth_doc.lower()
        assert 'producción clínica abierta' in lowered or 'produccion clinica abierta' in lowered
        assert 'fuera de alcance' in lowered or 'no habilita' in lowered


class TestProdMinRealDataEndpoints:
    def test_api_health(self, auth_doc: str):
        assert '/api/health/' in auth_doc

    def test_login(self, auth_doc: str):
        assert '/api/auth/login/' in auth_doc

    def test_current_user(self, auth_doc: str):
        assert 'current-user' in auth_doc

    def test_pacientes_protegido(self, auth_doc: str):
        assert '/api/pacientes/' in auth_doc


class TestProdMinRealDataScopeTemplate:
    def test_objetivo(self, scope_template: str):
        assert 'Objetivo' in scope_template or 'objetivo' in scope_template.lower()

    def test_alcance(self, scope_template: str):
        assert 'Alcance' in scope_template or 'alcance' in scope_template.lower()

    def test_fuera_de_alcance(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'fuera de alcance' in lowered

    def test_responsables(self, scope_template: str):
        assert 'Responsable' in scope_template or 'responsable' in scope_template.lower()

    def test_modulos_permitidos(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'módulos permitidos' in lowered or 'modulos permitidos' in lowered

    def test_modulos_excluidos(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'módulos excluidos' in lowered or 'modulos excluidos' in lowered

    def test_usuarios_autorizados(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'usuarios autorizados' in lowered

    def test_datos_permitidos(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'datos permitidos' in lowered

    def test_datos_prohibidos(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'datos prohibidos' in lowered

    def test_fecha_inicio(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'fecha de inicio' in lowered

    def test_fecha_fin(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'fecha de fin' in lowered

    def test_criterios_go_nogo(self, scope_template: str):
        assert 'GO' in scope_template
        assert 'NO-GO' in scope_template

    def test_criterios_suspension(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'suspensión' in lowered or 'suspension' in lowered

    def test_evidencia_requerida(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'evidencia requerida' in lowered or 'evidencia' in lowered

    def test_template_no_phi(self, scope_template: str):
        assert 'PHI' in scope_template

    def test_template_no_secretos(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'secreto' in lowered or 'token' in lowered or 'password' in lowered

    def test_firma_autorizacion_externa(self, scope_template: str):
        lowered = scope_template.lower()
        assert 'firma' in lowered or 'autorización externa' in lowered or 'autorizacion externa' in lowered
        assert 'fuera del repo' in lowered or 'fuera del repositorio' in lowered


class TestProdMinRealDataDocumentSafety:
    @pytest.mark.parametrize('path', [AUTH_DOC, SCOPE_TEMPLATE])
    def test_sin_patrones_secreto_en_docs(self, path: Path):
        content = _read(path)
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(content), f'{path.name}: {pattern.pattern}'
