#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T backend python manage.py migrate profesionales
docker compose exec -T backend python manage.py migrate estudios
docker compose exec -T backend python manage.py sync_cehta_excel --dry-run
docker compose exec -T backend python manage.py sync_cehta_excel
echo "OK sync CEHTA"
