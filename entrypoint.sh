#!/usr/bin/env bash
# Entrypoint dev para imagen backend EMR (Docker Compose local).
# - Espera Postgres (DB_HOST:DB_PORT).
# - Migraciones solo si RUN_MIGRATIONS=true (no seeds ni datos destructivos).
# - Arranca runserver en 0.0.0.0:8000 (desarrollo).

set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"

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

exec python manage.py runserver 0.0.0.0:8000
