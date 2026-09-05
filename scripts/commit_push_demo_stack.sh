#!/usr/bin/env bash
# Commit + push stack demo (ejecutar en WSL si el agente no puede).
set -euo pipefail
cd "$(dirname "$0")/.."

git add \
  .env.example \
  .env.demo.example \
  .gitignore \
  .dockerignore \
  docs/dev-start.md \
  docs/demo-stack.md \
  emrctl \
  synesis/env_config.py \
  core/management/commands/seed_demo_marketing.py \
  docker-compose.demo.yml \
  deploy/Dockerfile.demo-nginx \
  deploy/nginx/nginx.demo.conf \
  frontend/package.json \
  frontend/package-lock.json \
  frontend/src/App.tsx \
  frontend/src/components/layout/Sidebar.tsx \
  frontend/src/components/patient360/PatientDashboard.tsx \
  frontend/src/pages/InternacionDashboard.tsx \
  frontend/src/pages/Login.tsx \
  frontend/src/pages/Pacientes.tsx \
  frontend/src/pages/Solicitudes.tsx \
  frontend/src/pages/Turnos.tsx \
  frontend/src/pages/laboratorio/MuestraConsultaPage.tsx \
  frontend/src/pages/laboratorio/OrdenLimsDetalle.tsx \
  frontend/src/pages/laboratorio/OrdenesLims.tsx \
  frontend/src/pages/portal/PortalHistoria.tsx \
  frontend/src/pages/portal/PortalHome.tsx \
  frontend/src/pages/portal/PortalResultados.tsx \
  frontend/src/pages/portal/PortalTurnos.tsx \
  frontend/src/pages/DemoLanding.tsx \
  frontend/src/demo/ \
  2>/dev/null || true

# Only commit if there is something staged
if git diff --cached --quiet; then
  echo "Nada nuevo para commitear (¿ya está en HEAD?)."
  git log -1 --oneline
  git status -sb
  exit 0
fi

git commit -m "$(cat <<'EOF'
feat(demo): tour marketing, seed MKTG y stack aislado :8081

Landing /demo, driver.js por rol, seed_demo_marketing, CSRF :3001,
y compose emr-demo con Postgres/volumen propios para no mezclar BD.
EOF
)"

git push origin master
git status -sb
git log -1 --oneline
