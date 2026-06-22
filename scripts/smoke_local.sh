#!/usr/bin/env bash
# Smoke mínimo local SYNESIS EMR/LIMS (mismos checks que .github/workflows/smoke.yml).
# Uso: scripts/smoke_local.sh
# Requisitos: venv con requirements.txt (p. ej. emr_env/) y Node 18+ con npm en frontend/.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "No es un repositorio git." >&2; exit 1; }

if [[ -x emr_env/bin/python ]]; then
  PYTHON=emr_env/bin/python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "No se encontró Python (emr_env/bin/python ni python3)." >&2
  exit 1
fi

export DB_ENGINE=django.db.backends.sqlite3
export DB_NAME=:memory:

echo "==> Backend: manage.py check"
"$PYTHON" manage.py check

echo "==> Backend: pytest usuarios/tests/ auditoria/tests/"
"$PYTHON" -m pytest usuarios/tests/ auditoria/tests/ -q

echo "==> Backend: pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py"
"$PYTHON" -m pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q

echo "==> Frontend: npm test (suite global)"
(
  cd frontend
  npm ci --legacy-peer-deps
  CI=true npm test -- --watchAll=false
)

echo "==> Frontend: npm run build (CI=false — warnings ESLint no bloquean compilación)"
(
  cd frontend
  CI=false npm run build
)

echo "Smoke local OK."
