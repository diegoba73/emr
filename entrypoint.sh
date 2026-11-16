#!/bin/bash
# Entrypoint backend EMR — PROD-2-A.
# - Espera Postgres (DB_HOST:DB_PORT).
# - Migraciones solo si RUN_MIGRATIONS=true.
# - Runtime: DJANGO_RUNTIME=runserver (dev) | gunicorn (prod/staging).
# - Demo read-only: if DB_ADMIN_USER is set and differs from DB_USER, migrate/seed
#   run as admin; then scripts/demo_ensure_readonly_role.py; gunicorn uses DB_USER.

set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
DJANGO_RUNTIME="${DJANGO_RUNTIME:-runserver}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
BIND_ADDR="${BIND_ADDR:-0.0.0.0:8000}"

# Preserve runtime credentials (demo RO role). Migrate/seed may temporarily use admin.
RUNTIME_DB_USER="${DB_USER:-postgres}"
RUNTIME_DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_ADMIN_USER="${DB_ADMIN_USER:-}"
DB_ADMIN_PASSWORD="${DB_ADMIN_PASSWORD:-}"
USE_DB_ADMIN=false
if [ -n "${DB_ADMIN_USER}" ] && [ "${DB_ADMIN_USER}" != "${RUNTIME_DB_USER}" ]; then
  if [ -z "${DB_ADMIN_PASSWORD}" ]; then
    echo "DB_ADMIN_USER set but DB_ADMIN_PASSWORD is empty" >&2
    exit 1
  fi
  USE_DB_ADMIN=true
fi

echo "Esperando Postgres en ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 60); do
  if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
    echo "Postgres disponible."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "Timeout esperando Postgres en ${DB_HOST}:${DB_PORT}" >&2
    exit 1
  fi
  sleep 1
done

if [ "${USE_DB_ADMIN}" = "true" ]; then
  export DB_USER="${DB_ADMIN_USER}"
  export DB_PASSWORD="${DB_ADMIN_PASSWORD}"
  echo "Usando DB_ADMIN_USER para migrate/seed/grants (${DB_ADMIN_USER})."
fi

if [ "${RUN_MIGRATIONS}" = "true" ]; then
  echo "Ejecutando migraciones (RUN_MIGRATIONS=true)..."
  python manage.py migrate --noinput
else
  echo "Migraciones omitidas (RUN_MIGRATIONS no es 'true')."
fi

RUN_SEED="${RUN_SEED:-false}"
if [ "${RUN_SEED}" = "true" ]; then
  echo "Ejecutando seed_data (RUN_SEED=true, idempotente)..."
  python manage.py seed_data
  echo "Cargando catálogo solicitud en papel..."
  python manage.py seed_catalogo_solicitud_papel
else
  echo "Seed omitido (RUN_SEED no es 'true')."
fi

if [ "${USE_DB_ADMIN}" = "true" ]; then
  # Role name/password are the runtime DB_USER/DB_PASSWORD.
  export DB_USER="${RUNTIME_DB_USER}"
  export DB_PASSWORD="${RUNTIME_DB_PASSWORD}"
  echo "Aplicando rol read-only demo (${RUNTIME_DB_USER})..."
  python scripts/demo_ensure_readonly_role.py
  # Keep runtime credentials for gunicorn/runserver.
  export DB_USER="${RUNTIME_DB_USER}"
  export DB_PASSWORD="${RUNTIME_DB_PASSWORD}"
fi

case "${DJANGO_RUNTIME}" in
  runserver)
    echo "Iniciando runtime de desarrollo (runserver)."
    exec python manage.py runserver "${BIND_ADDR}"
    ;;
  gunicorn)
    echo "Iniciando runtime productivo (gunicorn)."
    exec gunicorn synesis.wsgi:application \
      --bind "${BIND_ADDR}" \
      --workers "${GUNICORN_WORKERS}" \
      --timeout "${GUNICORN_TIMEOUT}"
    ;;
  *)
    echo "DJANGO_RUNTIME inválido: '${DJANGO_RUNTIME}'. Use 'runserver' o 'gunicorn'." >&2
    exit 1
    ;;
esac
