#!/usr/bin/env bash
# Entrypoint backend EMR — PROD-2-A.
# - Espera Postgres (DB_HOST:DB_PORT).
# - Migraciones solo si RUN_MIGRATIONS=true.
# - Runtime: DJANGO_RUNTIME=runserver (dev) | gunicorn (prod/staging).

set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
DJANGO_RUNTIME="${DJANGO_RUNTIME:-runserver}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
BIND_ADDR="${BIND_ADDR:-0.0.0.0:8000}"

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
