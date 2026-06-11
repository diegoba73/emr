"""
PROD-5 — Tests estáticos de backup/restore operativo (PostgreSQL + media).

No ejecuta pg_dump, tar ni restore real.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO_ROOT / 'deploy' / 'backup'

SCRIPTS = {
    'postgres': BACKUP_DIR / 'backup_postgres.example.sh',
    'media': BACKUP_DIR / 'backup_media.example.sh',
    'restore': BACKUP_DIR / 'restore_postgres.example.sh',
}

FORBIDDEN_IN_SCRIPTS = [
    re.compile(r'echo\s+.*PGPASSWORD', re.I),
    re.compile(r'echo\s+.*DATABASE_URL', re.I),
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.I),
    re.compile(r'\brm\s+-rf\s+/'),
    re.compile(r'\bdropdb\b', re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def postgres_script() -> str:
    return _read(SCRIPTS['postgres'])


@pytest.fixture(scope='module')
def media_script() -> str:
    return _read(SCRIPTS['media'])


@pytest.fixture(scope='module')
def restore_script() -> str:
    return _read(SCRIPTS['restore'])


class TestProdBackupScriptsExist:
    def test_backup_postgres_example_existe(self):
        assert SCRIPTS['postgres'].is_file()

    def test_backup_media_example_existe(self):
        assert SCRIPTS['media'].is_file()

    def test_restore_postgres_example_existe(self):
        assert SCRIPTS['restore'].is_file()

    def test_readme_existe(self):
        assert (BACKUP_DIR / 'README.md').is_file()


class TestProdBackupScriptSafety:
    @pytest.mark.parametrize('name', ['postgres', 'media', 'restore'])
    def test_usa_set_euo_pipefail(self, name: str):
        content = _read(SCRIPTS[name])
        assert 'set -euo pipefail' in content

    @pytest.mark.parametrize('name', ['postgres', 'media', 'restore'])
    def test_no_patrones_peligrosos(self, name: str):
        content = _read(SCRIPTS[name])
        for pattern in FORBIDDEN_IN_SCRIPTS:
            assert not pattern.search(content), f'{name}: {pattern.pattern}'

    def test_postgres_requiere_backup_dir(self, postgres_script: str):
        assert 'BACKUP_DIR:?BACKUP_DIR requerido' in postgres_script

    def test_postgres_genera_checksum(self, postgres_script: str):
        assert 'sha256sum' in postgres_script

    def test_media_requiere_media_root(self, media_script: str):
        assert 'MEDIA_ROOT:?MEDIA_ROOT requerido' in media_script

    def test_media_genera_checksum(self, media_script: str):
        assert 'sha256sum' in media_script

    def test_restore_exige_confirm_restore(self, restore_script: str):
        assert 'CONFIRM_RESTORE=true' in restore_script
        assert 'CONFIRM_RESTORE:-' in restore_script

    def test_restore_exige_backup_file(self, restore_script: str):
        assert 'BACKUP_FILE:?BACKUP_FILE requerido' in restore_script

    def test_restore_exige_target_explicito(self, restore_script: str):
        assert 'RESTORE_TARGET_DB:?RESTORE_TARGET_DB requerido' in restore_script

    def test_restore_bloquea_synesis_db_por_defecto(self, restore_script: str):
        assert 'synesis_db' in restore_script
        assert 'ALLOW_RESTORE_PRODUCTION_NAME' in restore_script

    def test_restore_verifica_checksum_si_existe(self, restore_script: str):
        assert 'sha256sum -c' in restore_script


class TestProdBackupGitignore:
    def test_gitignore_ignora_dumps(self):
        content = _read(REPO_ROOT / '.gitignore')
        assert '*.dump' in content
        assert '*.sql.gz' in content
        assert 'backups/' in content
        assert 'deploy/backup/output/' in content

    def test_gitignore_no_ignora_plantillas_example(self):
        content = _read(REPO_ROOT / '.gitignore')
        assert '.example.sh' not in content


class TestProdBackupDocumentation:
    def test_readme_db_y_media_obligatorios(self):
        content = _read(BACKUP_DIR / 'README.md')
        assert 'PostgreSQL' in content
        assert 'media' in content.lower()
        assert 'recuperación completa' in content.lower()

    def test_readme_restore_drill_staging(self):
        content = _read(BACKUP_DIR / 'README.md')
        assert 'staging' in content.lower()
        assert 'drill' in content.lower()

    def test_readme_no_commitear_backups(self):
        content = _read(BACKUP_DIR / 'README.md')
        assert 'commitear' in content.lower()

    def test_prod_runtime_documenta_prod5(self):
        content = _read(REPO_ROOT / 'docs_synesis/PROD_RUNTIME.md')
        assert 'PROD-5' in content
        assert 'deploy/backup/' in content

    def test_prod_checklist_documenta_prod5(self):
        content = _read(REPO_ROOT / 'docs_synesis/PROD_CHECKLIST.md')
        assert 'PROD-5' in content


class TestProdBackupComposeNoAutoJob:
    def test_compose_prod_no_cron_backup(self):
        content = _read(REPO_ROOT / 'docker-compose.prod.example.yml')
        lowered = content.lower()
        assert 'cron' not in lowered
        assert 'schedule' not in lowered


class TestProdBackupNginxUnchanged:
    def test_nginx_sigue_bloqueando_media(self):
        content = _read(REPO_ROOT / 'deploy/nginx/nginx.prod.example.conf')
        assert 'location /media/' in content
        assert 'deny all' in content


@pytest.mark.parametrize(
    'rel_path',
    [
        'deploy/backup/backup_postgres.example.sh',
        'deploy/backup/backup_media.example.sh',
        'deploy/backup/restore_postgres.example.sh',
    ],
)
def test_bash_syntax_ok(rel_path: str):
    path = REPO_ROOT / rel_path
    result = subprocess.run(
        ['bash', '-n', str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
