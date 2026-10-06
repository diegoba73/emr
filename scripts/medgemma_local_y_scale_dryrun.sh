#!/usr/bin/env bash
# Encender MedGemma local + dry-run de escala LabWin (sin --apply).
# Uso: bash scripts/medgemma_local_y_scale_dryrun.sh [/ruta/DATOS]
set -euo pipefail
cd "$(dirname "$0")/.."

DATOS="${1:-}"
if [[ -z "$DATOS" ]]; then
  for cand in \
    "/mnt/c/Users/diego/Downloads/SYNESIS_R2_Firebird_para_Cursor/DATOS" \
    "$HOME/Downloads/SYNESIS_R2_Firebird_para_Cursor/DATOS" \
    "data/labwin_firebird/DATOS" \
    "data/icpl/DATOS"
  do
    if [[ -f "$cand/RESULTS.csv" && -f "$cand/DETERS.csv" && -f "$cand/PACIENTES.csv" ]]; then
      DATOS="$cand"
      break
    fi
  done
fi

echo "== 1) Ollama + medgemma:4b =="
INSTALL_OLLAMA="${INSTALL_OLLAMA:-1}"
if ! command -v ollama >/dev/null 2>&1; then
  if [[ "$INSTALL_OLLAMA" == "1" ]]; then
    if ! command -v zstd >/dev/null 2>&1; then
      echo "Falta zstd (requerido por el instalador de Ollama). Instalando..."
      sudo apt-get update -qq
      sudo apt-get install -y zstd
    fi
    echo "Ollama no encontrado: instalando (curl install.sh)..."
    curl -fsSL https://ollama.com/install.sh | sh
    hash -r || true
    export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
  fi
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama sigue sin estar en PATH. Instalación manual:"
  echo "  curl -fsSL https://ollama.com/install.sh | sh"
  echo "Luego reejecutá este script."
  echo "Continúo con dry-run de escala (MedGemma queda pendiente)."
  SKIP_MEDGEMMA=1
else
  SKIP_MEDGEMMA=0
fi

if [[ "${SKIP_MEDGEMMA:-0}" == "0" ]]; then
  # Arrancar serve en background si no responde
  if ! curl -sf --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Iniciando ollama serve..."
    nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
    sleep 3
  fi
  ollama pull medgemma:4b
  curl -sf http://127.0.0.1:11434/api/tags | head -c 400 || true
  echo
fi

if [[ "${SKIP_MEDGEMMA:-0}" == "0" ]]; then
  # Asegurar .env
  if ! grep -q '^MEDGEMMA_ENABLED=' .env 2>/dev/null; then
    cat >> .env <<'EOF'

# --- MedGemma / Ollama (solo local) ---
MEDGEMMA_ENABLED=true
MEDGEMMA_BASE_URL=http://host.docker.internal:11434
MEDGEMMA_MODEL=medgemma:4b
MEDGEMMA_TIMEOUT_SECONDS=90
EOF
  else
    sed -i 's/^MEDGEMMA_ENABLED=.*/MEDGEMMA_ENABLED=true/' .env
    sed -i 's/^#*MEDGEMMA_ENABLED=.*/MEDGEMMA_ENABLED=true/' .env || true
    grep -q '^MEDGEMMA_BASE_URL=' .env || echo 'MEDGEMMA_BASE_URL=http://host.docker.internal:11434' >> .env
    grep -q '^MEDGEMMA_MODEL=' .env || echo 'MEDGEMMA_MODEL=medgemma:4b' >> .env
    grep -q '^MEDGEMMA_TIMEOUT_SECONDS=' .env || echo 'MEDGEMMA_TIMEOUT_SECONDS=90' >> .env
    sed -i 's|^MEDGEMMA_BASE_URL=.*|MEDGEMMA_BASE_URL=http://host.docker.internal:11434|' .env
    sed -i 's|^MEDGEMMA_MODEL=.*|MEDGEMMA_MODEL=medgemma:4b|' .env
    sed -i 's|^MEDGEMMA_TIMEOUT_SECONDS=.*|MEDGEMMA_TIMEOUT_SECONDS=90|' .env
  fi

  echo "== Restart backend (recarga .env) =="
  if [[ -x ./emrctl ]]; then
    ./emrctl up >/dev/null || docker compose restart backend || true
  else
    docker compose restart backend || docker restart emr_backend || true
  fi
  sleep 3

  echo "== Reachability desde contenedor =="
  docker exec emr_backend python - <<'PY' || true
import urllib.request
for url in (
    "http://host.docker.internal:11434/api/tags",
    "http://172.17.0.1:11434/api/tags",
):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            print(url, "OK", r.status)
            break
    except Exception as e:
        print(url, "FAIL", e)
PY
fi

echo "== 2) Scale dry-run (until 2026-09-29, sin apply) =="
if [[ -z "${DATOS:-}" || ! -d "$DATOS" ]]; then
  echo "No encontré DATOS (DETERS/PACIENTES/RESULTS). Pasá la ruta:"
  echo "  bash scripts/medgemma_local_y_scale_dryrun.sh /ruta/DATOS"
  exit 0
fi
echo "DATOS=$DATOS"

# DATOS suele estar fuera del mount .:/app. Usar compose run con --entrypoint ""
# (si no, el entrypoint arranca runserver y traga el manage.py).
run_mgmt() {
  local cmd="$1"
  shift || true
  local extra=("$@")
  if docker exec emr_backend test -f "$DATOS/RESULTS.csv" 2>/dev/null; then
    docker exec emr_backend python manage.py "$cmd" "$DATOS" \
      --until 2026-09-29 --all-firebird-overlap "${extra[@]}"
  else
    docker compose run --rm \
      -e RUN_MIGRATIONS=false \
      -e RUN_SEED=false \
      --entrypoint "" \
      -v "$DATOS:/datos_labwin:ro" \
      backend \
      python manage.py "$cmd" /datos_labwin \
      --until 2026-09-29 --all-firebird-overlap "${extra[@]}"
  fi
}

echo "--- audit ---"
run_mgmt audit_labwin_firebird_scale
echo "--- rectify dry-run (include-finalized) ---"
run_mgmt rectify_labwin_firebird_scale --include-finalized

echo
echo "DONE. Sin --apply. Revisá conteos (scale_error, fixable, skipped_after_until)."
echo "Si MedGemma no alcanza desde Docker, probá MEDGEMMA_BASE_URL=http://172.17.0.1:11434"
