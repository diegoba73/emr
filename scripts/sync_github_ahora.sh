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

# Guardrail: no subir migraciones con el mismo número (salvo merge_*).
dupes=$(ls laboratorio/migrations/0*.py 2>/dev/null \
  | xargs -n1 basename \
  | sed -E 's/^([0-9]+).*/\1/' \
  | sort | uniq -d || true)
if [[ -n "${dupes}" ]]; then
  echo "Hay números de migración duplicados: ${dupes}" >&2
  ls -1 laboratorio/migrations/0*.py | grep -E "^laboratorio/migrations/(${dupes//$'\n'/|})" || \
    ls -1 laboratorio/migrations/0*.py
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "Nada para commitear."
else
  git commit -m "$(cat <<'EOF'
feat(lims): orinas 24h calculadas, hisopado anal, PDFs/talón, día operativo IQC

Añade PROT_U_24/iones/microalb 24h calculados, tipo cultivo HISOPADO_ANAL,
orden de presentación en talón/informe, gate QC por día operativo (corte 8h)
y ajustes de orina micro, hemograma y docs.

Co-authored-by: Cursor <cursoragent@cursor.com>
EOF
)"
fi

git push origin master
git status -sb
git log -1 --oneline
git rev-parse HEAD
echo
echo "=== LOCAL (Docker) después del push ==="
echo "  docker exec emr_backend python manage.py migrate --noinput"
echo "  docker exec emr_backend python manage.py seed_catalogo_solicitud_papel"
echo "  # frontend: reiniciar npm start o rebuild si usás Docker frontend"
echo
echo "=== PRODUCCIÓN (ssh -p 2223 server@emr.sytes.net) ==="
echo "  cd /srv/emr/app"
echo "  git status --short"
echo "  git fetch origin && git merge --no-edit origin/master"
echo "  bash scripts/deploy_mobile_server.sh"
