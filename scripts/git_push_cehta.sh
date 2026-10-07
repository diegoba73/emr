#!/usr/bin/env bash
set -euo pipefail
cd /home/diego/proyectos/emr
git add -A
git reset -- reportes/ || true
# no secrets
git reset -- '*.env' '.env' '.env.*' 2>/dev/null || true
git status --short | head -80
git commit -m "$(cat <<'EOF'
CEHTA sync (profesionales, practica, consultorios), guardia for secretaria, micro order edit, and related LIMS/UI updates.

EOF
)" || {
  echo "COMMIT_FAILED_OR_EMPTY"
  git status
  exit 1
}
git push origin HEAD
git log -1 --oneline
git status -sb
