"""
PROD-2-A / PROD-2-B — tests de configuración y ejecución del runtime productivo.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / 'entrypoint.sh'
DUMMY_SECRET = 'dummy-secret-for-test-only-not-real'


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding='utf-8')


def _nginx_service_block(compose_content: str) -> str:
    """Bloque del servicio nginx (excluye volumes: raíz del compose)."""
    block = compose_content.split('nginx:', 1)[1]
    if '\nvolumes:' in block:
        block = block.split('\nvolumes:', 1)[0]
    return block


def _make_stub_bin(tmp_path: Path) -> tuple[Path, Path]:
    """Binarios falsos en PATH para evitar Postgres, migraciones y servidores reales."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    log_file = tmp_path / 'stub.log'
    log = str(log_file)

    def write_stub(name: str, content: str) -> None:
        path = bin_dir / name
        path.write_text(content, encoding='utf-8')
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    write_stub(
        'nc',
        """#!/usr/bin/env bash
exit 0
""",
    )
    write_stub(
        'sleep',
        """#!/usr/bin/env bash
exit 0
""",
    )
    write_stub(
        'python',
        f"""#!/usr/bin/env bash
echo "PYTHON: $*" >> "{log}"
exit 0
""",
    )
    write_stub(
        'gunicorn',
        f"""#!/usr/bin/env bash
echo "GUNICORN: $*" >> "{log}"
exit 0
""",
    )
    return bin_dir, log_file


def _run_entrypoint(
    tmp_path: Path,
    bin_dir: Path,
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        'PATH': f'{bin_dir}:{os.environ.get("PATH", "")}',
        'DB_HOST': '127.0.0.1',
        'DB_PORT': '5432',
        'RUN_MIGRATIONS': 'false',
        'DJANGO_RUNTIME': 'runserver',
        'BIND_ADDR': '0.0.0.0:8000',
        'SECRET_KEY': DUMMY_SECRET,
        'DJANGO_SECRET_KEY': DUMMY_SECRET,
    }
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ['bash', str(ENTRYPOINT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=15,
        check=False,
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f'{result.stdout}\n{result.stderr}'


def _assert_no_secrets(output: str) -> None:
    assert DUMMY_SECRET not in output
    assert 'dummy-secret-for-test' not in output.lower()


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


class TestEntrypointExecutable:
    def test_runtime_invalido_falla_con_mensaje_claro(self, tmp_path: Path):
        bin_dir, _ = _make_stub_bin(tmp_path)
        result = _run_entrypoint(
            tmp_path,
            bin_dir,
            env_overrides={'DJANGO_RUNTIME': 'invalid'},
        )
        output = _combined_output(result)

        assert result.returncode == 1
        assert 'DJANGO_RUNTIME inválido' in output
        assert 'invalid' in output
        _assert_no_secrets(output)

    def test_runtime_runserver_invoca_manage_py_runserver(self, tmp_path: Path):
        bin_dir, log_file = _make_stub_bin(tmp_path)
        bind_addr = '127.0.0.1:8765'
        result = _run_entrypoint(
            tmp_path,
            bin_dir,
            env_overrides={
                'DJANGO_RUNTIME': 'runserver',
                'BIND_ADDR': bind_addr,
            },
        )
        output = _combined_output(result)
        stub_log = log_file.read_text(encoding='utf-8')

        assert result.returncode == 0
        assert 'Iniciando runtime de desarrollo (runserver)' in output
        assert 'manage.py runserver' in stub_log
        assert bind_addr in stub_log
        _assert_no_secrets(output)

    def test_runtime_gunicorn_invoca_wsgi_con_bind_addr(self, tmp_path: Path):
        bin_dir, log_file = _make_stub_bin(tmp_path)
        bind_addr = '0.0.0.0:9001'
        result = _run_entrypoint(
            tmp_path,
            bin_dir,
            env_overrides={
                'DJANGO_RUNTIME': 'gunicorn',
                'BIND_ADDR': bind_addr,
                'GUNICORN_WORKERS': '2',
                'GUNICORN_TIMEOUT': '90',
            },
        )
        output = _combined_output(result)
        stub_log = log_file.read_text(encoding='utf-8')

        assert result.returncode == 0
        assert 'Iniciando runtime productivo (gunicorn)' in output
        assert 'synesis.wsgi:application' in stub_log
        assert f'--bind {bind_addr}' in stub_log
        assert '--workers 2' in stub_log
        assert '--timeout 90' in stub_log
        _assert_no_secrets(output)

    def test_run_migrations_false_no_invoca_migrate(self, tmp_path: Path):
        bin_dir, log_file = _make_stub_bin(tmp_path)
        result = _run_entrypoint(
            tmp_path,
            bin_dir,
            env_overrides={
                'RUN_MIGRATIONS': 'false',
                'DJANGO_RUNTIME': 'gunicorn',
            },
        )
        output = _combined_output(result)
        stub_log = log_file.read_text(encoding='utf-8')

        assert result.returncode == 0
        assert 'Migraciones omitidas' in output
        assert 'migrate' not in stub_log
        _assert_no_secrets(output)

    def test_run_migrations_true_invoca_migrate(self, tmp_path: Path):
        bin_dir, log_file = _make_stub_bin(tmp_path)
        result = _run_entrypoint(
            tmp_path,
            bin_dir,
            env_overrides={
                'RUN_MIGRATIONS': 'true',
                'DJANGO_RUNTIME': 'gunicorn',
            },
        )
        output = _combined_output(result)
        stub_log = log_file.read_text(encoding='utf-8')

        assert result.returncode == 0
        assert 'Ejecutando migraciones' in output
        assert 'manage.py migrate --noinput' in stub_log
        _assert_no_secrets(output)

    def test_salida_no_contiene_secret_key_dummy(self, tmp_path: Path):
        bin_dir, _ = _make_stub_bin(tmp_path)
        for runtime in ('runserver', 'gunicorn', 'invalid'):
            result = _run_entrypoint(
                tmp_path,
                bin_dir,
                env_overrides={'DJANGO_RUNTIME': runtime},
            )
            _assert_no_secrets(_combined_output(result))


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

    def test_prod_example_tiene_healthcheck_http(self):
        content = _read('docker-compose.prod.example.yml')
        assert 'healthcheck:' in content
        assert '/api/health/' in content

    def test_prod_example_incluye_servicio_nginx(self):
        content = _read('docker-compose.prod.example.yml')
        assert 'nginx:' in content
        assert 'nginx.prod.example.conf' in content

    def test_prod_example_backend_no_publica_puerto_8000(self):
        content = _read('docker-compose.prod.example.yml')
        assert '8000:8000' not in content
        assert 'expose:' in content

    def test_prod_nginx_depende_backend_healthy(self):
        content = _read('docker-compose.prod.example.yml')
        nginx_block = content.split('nginx:', 1)[1]
        assert 'depends_on:' in nginx_block
        assert 'backend:' in nginx_block
        assert 'condition: service_healthy' in nginx_block
        backend_block = content.split('backend:', 1)[1].split('nginx:', 1)[0]
        assert 'depends_on:' in backend_block
        assert 'db:' in backend_block
        assert 'nginx:' not in backend_block.split('depends_on:', 1)[1].split('healthcheck:', 1)[0]

    def test_prod_nginx_no_monta_volumen_media(self):
        content = _read('docker-compose.prod.example.yml')
        nginx_block = _nginx_service_block(content)
        nginx_volumes = nginx_block.split('volumes:', 1)[1].split('depends_on:', 1)[0]
        assert 'media' not in nginx_volumes.lower()
        assert 'MEDIA_ROOT' not in nginx_block


class TestProdPrivateMediaStorage:
    """PROD-4 — media clínica privada; sin serving público Nginx/Django en producción."""

    def test_compose_prod_documenta_media_privada(self):
        content = _read('docker-compose.prod.example.yml')
        assert 'PROD-4' in content or 'media' in content.lower()

    def test_compose_prod_nginx_sin_volumen_media(self):
        content = _read('docker-compose.prod.example.yml')
        nginx_block = _nginx_service_block(content)
        nginx_volumes = nginx_block.split('volumes:', 1)[1].split('depends_on:', 1)[0]
        assert 'nginx.prod.example.conf' in nginx_volumes
        assert 'media' not in nginx_volumes.lower()

    def test_env_production_sin_credenciales_storage_cloud(self):
        content = _read('.env.production.example').lower()
        for token in (
            'aws_secret_access_key',
            'aws_access_key',
            'minio_root_password',
            's3_secret',
            'minio_access',
        ):
            assert token not in content

    def test_env_production_documenta_media_privada(self):
        content = _read('.env.production.example')
        assert 'PROD-4' in content or 'media' in content.lower()
        assert 'endpoints protegidos' in content.lower() or 'storage privado' in content.lower()

    def test_prod_runtime_doc_declara_media_privada(self):
        content = _read('docs_synesis/PROD_RUNTIME.md')
        assert 'PROD-4' in content
        assert '/media/' in content
        assert 'endpoints protegidos' in content.lower() or 'privad' in content.lower()

    def test_prod_checklist_declara_media_privada(self):
        content = _read('docs_synesis/PROD_CHECKLIST.md')
        assert 'PROD-4' in content or 'storage privado' in content.lower()
        assert '/media/' in content

    def test_doc_backend_declara_media_protegida(self):
        content = _read('docs_synesis/DOC_BACKEND.md')
        assert 'PROD-4' in content or 'endpoints protegidos' in content.lower()
        assert 'DEBUG=True' in content


class TestDockerComposeProdHealthcheck:
    """Validación estática del healthcheck prod (sin levantar contenedores)."""

    @pytest.fixture
    def prod_compose(self) -> str:
        return _read('docker-compose.prod.example.yml')

    def test_healthcheck_usa_api_health(self, prod_compose: str):
        assert '/api/health/' in prod_compose

    def test_healthcheck_usa_django_healthcheck_host(self, prod_compose: str):
        assert 'DJANGO_HEALTHCHECK_HOST' in prod_compose
        assert "os.getenv('DJANGO_HEALTHCHECK_HOST'" in prod_compose

    def test_healthcheck_usa_header_host_controlado(self, prod_compose: str):
        assert "'Host': host" in prod_compose

    def test_healthcheck_usa_x_forwarded_proto_https(self, prod_compose: str):
        assert 'X-Forwarded-Proto' in prod_compose
        assert "'X-Forwarded-Proto': 'https'" in prod_compose

    def test_healthcheck_usa_python_urllib_sin_curl_ni_wget(self, prod_compose: str):
        health_block = prod_compose.split('healthcheck:', 1)[1]
        assert 'urllib.request' in health_block
        assert 'curl' not in health_block.lower()
        assert 'wget' not in health_block.lower()

    def test_healthcheck_no_hardcodea_secretos(self, prod_compose: str):
        probe_start = prod_compose.index('import os, urllib.request')
        probe_end = prod_compose.index('timeout=5)', probe_start) + len('timeout=5)')
        probe_cmd = prod_compose[probe_start:probe_end].lower()
        assert 'secret' not in probe_cmd
        assert 'password' not in probe_cmd
        assert 'django-insecure' not in probe_cmd


class TestNginxProdExample:
    """Validación estática de plantilla Nginx (PROD-3; sin levantar Nginx)."""

    @pytest.fixture
    def nginx_conf(self) -> str:
        return _read('deploy/nginx/nginx.prod.example.conf')

    def test_nginx_prod_example_existe(self):
        assert (REPO_ROOT / 'deploy/nginx/nginx.prod.example.conf').is_file()

    def test_nginx_proxy_a_backend_gunicorn(self, nginx_conf: str):
        assert 'backend:8000' in nginx_conf
        assert 'proxy_pass http://django_backend' in nginx_conf

    def test_nginx_preserva_header_host(self, nginx_conf: str):
        assert 'proxy_set_header Host $host' in nginx_conf

    def test_nginx_preserva_x_forwarded_for(self, nginx_conf: str):
        assert 'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for' in nginx_conf

    def test_nginx_preserva_x_forwarded_proto(self, nginx_conf: str):
        assert 'map $http_x_forwarded_proto $proxy_x_forwarded_proto' in nginx_conf
        assert 'proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto' in nginx_conf

    def test_nginx_no_fuerza_siempre_scheme_en_proto(self, nginx_conf: str):
        assert "default $http_x_forwarded_proto" in nginx_conf
        assert "''      $scheme" in nginx_conf
        assert 'proxy_set_header X-Forwarded-Proto $scheme' not in nginx_conf

    def test_nginx_preserva_x_real_ip(self, nginx_conf: str):
        assert 'proxy_set_header X-Real-IP $remote_addr' in nginx_conf

    def test_nginx_bloquea_dotfiles(self, nginx_conf: str):
        assert 'location ~ /\\.(?!well-known).*' in nginx_conf
        assert 'deny all' in nginx_conf

    def test_nginx_no_expone_media_publicamente(self, nginx_conf: str):
        assert 'location /media/' in nginx_conf
        media_block = nginx_conf.split('location /media/', 1)[1].split('location', 1)[0]
        assert 'deny all' in media_block or 'return 404' in media_block

    def test_nginx_no_alias_publico_a_media(self, nginx_conf: str):
        lowered = nginx_conf.lower()
        assert 'alias' not in lowered
        assert 'root /' not in lowered.replace('root /var/www/certbot', '')

    def test_nginx_no_autoindex(self, nginx_conf: str):
        assert 'autoindex' not in nginx_conf.lower()

    def test_nginx_no_contiene_secretos_ni_certificados_reales(self, nginx_conf: str):
        lowered = nginx_conf.lower()
        assert 'begin certificate' not in lowered
        assert 'private_key' not in lowered.replace('_', '')
        assert 'django-insecure' not in lowered
        assert 'server_name example.com' in nginx_conf


class TestEnvExamples:
    def test_env_production_example_usa_gunicorn(self):
        content = _read('.env.production.example')
        assert 'DJANGO_RUNTIME=gunicorn' in content

    def test_env_production_example_declara_healthcheck_host(self):
        content = _read('.env.production.example')
        assert 'DJANGO_HEALTHCHECK_HOST=' in content

    def test_env_production_example_documenta_reverse_proxy(self):
        content = _read('.env.production.example')
        assert 'PROD-3' in content or 'nginx.prod.example.conf' in content
        assert 'DJANGO_USE_PROXY_SSL_HEADER' in content

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
        'deploy/nginx/nginx.prod.example.conf',
    ],
)
def test_doc_runtime_existe(rel_path: str):
    assert (REPO_ROOT / rel_path).is_file()
