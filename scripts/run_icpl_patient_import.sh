#!/usr/bin/env bash
# Importa pacientes ICPL desde PACIENTES.csv (idempotente con --update-existing).
set -euo pipefail
cd "$(dirname "$0")/.."

CSV_DEFAULT="data/icpl/PACIENTES.csv"
SRC="${ICPL_PACIENTES_SRC:-/mnt/g/Mi unidad/laboratorio_ICPL/PACIENTES.csv}"
CSV="${1:-$CSV_DEFAULT}"

mkdir -p "$(dirname "$CSV")"
if [[ -f "$SRC" && ! -f "$CSV" ]]; then
  cp "$SRC" "$CSV"
fi

if [[ ! -f "$CSV" ]]; then
  echo "No se encontró CSV: $CSV (origen: $SRC)" >&2
  exit 1
fi

echo "=== pytest ==="
python3 -m pytest pacientes/tests/test_icpl_csv_import.py -q

run_import() {
  python3 manage.py import_pacientes_icpl_csv "$CSV" "$@"
}

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q emr; then
  echo "=== dry-run (docker) ==="
  docker compose exec -T backend python manage.py import_pacientes_icpl_csv "$CSV" --dry-run
  echo "=== import (docker) ==="
  docker compose exec -T backend python manage.py import_pacientes_icpl_csv "$CSV" --update-existing
else
  export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-synesis.settings}"
  echo "=== dry-run (local) ==="
  run_import --dry-run
  echo "=== import (local) ==="
  run_import --update-existing
fi
