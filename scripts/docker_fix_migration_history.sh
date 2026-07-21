#!/usr/bin/env bash
# Repara historial de migraciones y aplica pendientes en el contenedor backend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! docker compose ps db 2>/dev/null | grep -q "Up"; then
  echo "Postgres no está corriendo. Ejecutá: ./emrctl up"
  exit 1
fi

echo "==> Aplicando migraciones pendientes..."
docker compose exec -T backend python manage.py migrate --noinput

echo "==> Verificando migraciones pendientes..."
docker compose exec -T backend python manage.py showmigrations --plan | tail -20

echo "✅ Migraciones aplicadas."
