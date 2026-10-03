#!/usr/bin/env bash
# Commit + push de cambios locales LIMS a origin/master.
# Uso (en WSL): bash scripts/sync_github_ahora.sh
set -euo pipefail
cd "$(dirname "$0")/.."

git status -sb
if git status --porcelain | grep -E '\.env($|\.|/)|credentials|\.pem$|\.key$' >/dev/null; then
  echo "Hay archivos sensibles en el working tree; abortando." >&2
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "Nada para commitear."
else
  git commit -m "$(cat <<'EOF'
feat(lims): restricciones, clearance calculado, búsqueda QC/inventario y orden ascendente

Amplía restricciones de ensayos, CLEAR_CREA calculado, solicitud papel/UI, búsqueda en QC e inventario, número de orden ascendente, etiquetas micro y docs Synesis.

Co-authored-by: Cursor <cursoragent@cursor.com>
EOF
)"
fi

git push origin master
git status -sb
git log -1 --oneline
git rev-parse HEAD
echo
echo "GitHub OK. En producción (ssh -p 2223 server@emr.sytes.net):"
echo "  cd /srv/emr/app && git fetch origin && git merge --no-edit origin/master"
echo "  luego: bash scripts/deploy_mobile_server.sh"
echo "  (o el flujo de docs/despliegue-20260924.md si preferís ese script)"
