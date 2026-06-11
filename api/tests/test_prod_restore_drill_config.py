"""
PROD-5-A — Tests estáticos del restore drill en staging.

No ejecuta restore real ni requiere PostgreSQL.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO_ROOT / 'deploy' / 'backup'
DRILL_DOC = BACKUP_DIR / 'RESTORE_DRILL_STAGING.md'
VERIFY_SCRIPT = BACKUP_DIR / 'verify_restore.example.sh'

FORBIDDEN_IN_DOCS = [
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.I),
    re.compile(r'DATABASE_URL=postgres://[^:]+:[^@]+@'),
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def drill_doc() -> str:
    return _read(DRILL_DOC)


@pytest.fixture(scope='module')
def verify_script() -> str:
    return _read(VERIFY_SCRIPT)


class TestProdRestoreDrillDocument:
    def test_restore_drill_staging_md_existe(self):
        assert DRILL_DOC.is_file()

    def test_menciona_staging_o_temporal(self, drill_doc: str):
        lowered = drill_doc.lower()
        assert 'staging' in lowered
        assert 'temporal' in lowered or 'aislado' in lowered

    def test_prohibe_produccion(self, drill_doc: str):
        lowered = drill_doc.lower()
        assert 'producción' in lowered or 'produccion' in lowered
        assert 'no' in lowered and ('restaurar' in lowered or 'ejecutar' in lowered)

    def test_exige_confirm_restore(self, drill_doc: str):
        assert 'CONFIRM_RESTORE=true' in drill_doc

    def test_exige_restore_target_db(self, drill_doc: str):
        assert 'RESTORE_TARGET_DB' in drill_doc

    def test_exige_backup_file(self, drill_doc: str):
        assert 'BACKUP_FILE' in drill_doc

    def test_exige_media_restore_dir(self, drill_doc: str):
        assert 'MEDIA_RESTORE_DIR' in drill_doc

    def test_exige_checksum(self, drill_doc: str):
        assert 'sha256' in drill_doc.lower() or 'checksum' in drill_doc.lower()

    def test_media_privada(self, drill_doc: str):
        lowered = drill_doc.lower()
        assert 'privad' in lowered or 'nginx' in lowered

    def test_media_bloqueada_nginx(self, drill_doc: str):
        assert '/media/' in drill_doc
        assert 'deny' in drill_doc.lower() or 'bloqueado' in drill_doc.lower()

    def test_no_commitear_phi(self, drill_doc: str):
        lowered = drill_doc.lower()
        assert 'phi' in lowered
        assert 'commitear' in lowered or 'no commitear' in lowered

    def test_checklist_post_restore(self, drill_doc: str):
        assert 'post-restore' in drill_doc.lower() or 'verificación' in drill_doc.lower()

    def test_conteos_agregados_sin_phi(self, drill_doc: str):
        assert 'COUNT(*)' in drill_doc
        assert 'pacientes_paciente' in drill_doc
        assert 'laboratorio_solicitudexamen' in drill_doc

    def test_no_secretos_ni_dominios_reales(self, drill_doc: str):
        for pattern in FORBIDDEN_IN_DOCS:
            assert not pattern.search(drill_doc), pattern.pattern


class TestProdRestoreDrillVerifyScript:
    def test_verify_restore_example_existe(self):
        assert VERIFY_SCRIPT.is_file()

    def test_usa_set_euo_pipefail(self, verify_script: str):
        assert 'set -euo pipefail' in verify_script

    def test_exige_confirm_drill_verify(self, verify_script: str):
        assert 'CONFIRM_DRILL_VERIFY=true' in verify_script

    def test_exige_restore_target_db(self, verify_script: str):
        assert 'RESTORE_TARGET_DB:?RESTORE_TARGET_DB requerido' in verify_script

    def test_bloquea_synesis_db_por_defecto(self, verify_script: str):
        assert 'synesis_db' in verify_script

    def test_verifica_checksum_si_existe(self, verify_script: str):
        assert 'sha256sum -c' in verify_script

    def test_conteos_solo_count(self, verify_script: str):
        assert 'COUNT(*)' in verify_script
        assert 'SELECT * FROM pacientes' not in verify_script.replace('COUNT(*)', '')


class TestProdRestoreDrillProd5Intact:
    def test_gitignore_sigue_protegiendo_backups(self):
        content = _read(REPO_ROOT / '.gitignore')
        assert '*.dump' in content
        assert 'backups/' in content

    def test_prod5_scripts_bash_n(self):
        for name in (
            'backup_postgres.example.sh',
            'backup_media.example.sh',
            'restore_postgres.example.sh',
            'verify_restore.example.sh',
        ):
            path = BACKUP_DIR / name
            result = subprocess.run(
                ['bash', '-n', str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, f'{name}: {result.stderr}'


@pytest.mark.parametrize(
    'rel_path',
    ['deploy/backup/RESTORE_DRILL_STAGING.md', 'deploy/backup/verify_restore.example.sh'],
)
def test_prod5a_files_exist(rel_path: str):
    assert (REPO_ROOT / rel_path).is_file()
