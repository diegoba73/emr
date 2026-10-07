#!/usr/bin/env bash
# Commit + push Filtros avanzados / LabWin scale / analytics / LPA export
# SIN MedGemma/Ollama ni Excel con PHI.
# Uso (WSL, repo root):
#   bash scripts/push_filtros_avanzados_sin_medgemma.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== estado =="
git status -sb
git rev-parse --abbrev-ref HEAD

# --- INCLUDE (archivos enteros seguros) ---
INCLUDE=(
  laboratorio/cohortes_filtros.py
  laboratorio/views_filtros_avanzados.py
  laboratorio/tests/test_filtros_avanzados.py
  frontend/src/pages/laboratorio/FiltrosAvanzadosPage.tsx
  laboratorio/analytics_resultados.py
  laboratorio/views_analytics.py
  laboratorio/tests/test_analytics_resultados.py
  frontend/src/pages/laboratorio/AnalyticsAnalitosPage.tsx
  laboratorio/labwin_firebird_scope.py
  laboratorio/tests/test_labwin_firebird_scope.py
  laboratorio/management/commands/audit_labwin_firebird_scale.py
  laboratorio/management/commands/rectify_labwin_firebird_scale.py
  laboratorio/scripts_check_labwin_scale.sh
  docs_synesis/DOC_LABWIN_ESCALA_DECIMAL.md
  laboratorio/management/commands/exportar_pacientes_lpa.py
  laboratorio/tests/test_exportar_pacientes_lpa.py
  frontend/src/components/layout/Sidebar.tsx
  frontend/src/utils/limsAccess.ts
  frontend/src/App.tsx
  frontend/src/services/limsApi.ts
  api/urls.py
)

# --- EXCLUDE explícito (no agregar aunque existan) ---
EXCLUDE_GLOBS=(
  'laboratorio/medgemma_client.py'
  'laboratorio/sugerir_interpretacion.py'
  'laboratorio/tests/test_sugerir_interpretacion.py'
  'laboratorio/tests/test_medgemma_client.py'
  'frontend/src/components/lims/SugerirInterpretacionPanel.tsx'
  'docs/medgemma-ollama.md'
  'docs_synesis/reglas/ia.md'
  'scripts/medgemma*'
  'docker-compose.yml'
  '.env'
  '.env.example'
  'synesis/settings.py'
  'docs/dev-start.md'
  'reportes/*.xlsx'
  'reportes/*.xls'
)

echo "== verificando que no stageamos MedGemma/PHI =="
for g in "${EXCLUDE_GLOBS[@]}"; do
  # shellcheck disable=SC2086
  if git status --porcelain -- $g 2>/dev/null | grep -q .; then
    echo "  (queda fuera) $g"
  fi
done

echo "== stage INCLUDE =="
for f in "${INCLUDE[@]}"; do
  if [[ -e "$f" ]]; then
    git add -- "$f"
    echo "  + $f"
  else
    echo "  (skip missing) $f"
  fi
done

# REGLAS_INDICE solo si el diff no es solo MedGemma — por defecto NO
# CargaResultados / SolicitudLabDetalle / views.py: NO (suelen enganchar MedGemma)

echo "== staged =="
git diff --cached --stat
if git diff --cached --quiet; then
  echo "Nada staged. Abort."
  exit 1
fi

# Guardia: líneas nuevas del stage no deben meter MedGemma/Ollama
if git diff --cached -U0 | grep -E '^\+' | grep -Ev '^\+\+\+' | grep -Eiq 'medgemma|ollama|MEDGEMMA_|SugerirInterpretacion'; then
  echo "ERROR: el stage agrega líneas MedGemma/Ollama. Revisá y deshacé:"
  echo "  git restore --staged ."
  git diff --cached --name-only
  exit 1
fi

git commit -m "$(cat <<'EOF'
feat(lims): filtros avanzados de cohortes por exámenes y Excel

Menú Principal (al final). Modo Algunos con obligatorios que definen la
cohorte y columnas opcionales. Incluye analytics de analitos, tooling de
escala LabWin y export LPA. Sin MedGemma/Ollama.
EOF
)"

echo "== push =="
git push -u origin HEAD

echo "== listo =="
git status -sb
git log -2 --oneline
