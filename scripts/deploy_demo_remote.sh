#!/usr/bin/env bash
# Deploy stack DEMO en el servidor EMR (SSH :2223). NO tocar stack clínico ni app :22.
# Uso (desde tu máquina con clave SSH):
#   bash scripts/deploy_demo_remote.sh
set -euo pipefail

REMOTE="${DEMO_SSH:-server@dsachubut.sytes.net}"
PORT="${DEMO_SSH_PORT:-2223}"
# Ajustá si el repo en el servidor está en otra ruta
REMOTE_DIR="${DEMO_REMOTE_DIR:-/srv/emr/app}"

ssh -p "$PORT" "$REMOTE" bash -s <<EOF
set -euo pipefail
cd ${REMOTE_DIR}
git pull origin master
cp -n .env.demo.example .env.demo || true
# Asegurar CSRF/hosts de demo pública (idempotente si ya están)
grep -q 'dsachubut.sytes.net:8081' .env.demo || cat >> .env.demo <<'ENV'

# --- hosts demo pública ---
DJANGO_ALLOWED_HOSTS=dsachubut.sytes.net,localhost,127.0.0.1
DJANGO_CORS_ALLOWED_ORIGINS=http://dsachubut.sytes.net:8081,http://localhost:8081
DJANGO_CSRF_TRUSTED_ORIGINS=http://dsachubut.sytes.net:8081,http://localhost:8081
ENV

docker compose -p emr-demo -f docker-compose.demo.yml --env-file .env.demo up -d --build
docker compose -p emr-demo -f docker-compose.demo.yml exec -T backend python manage.py seed_data
docker compose -p emr-demo -f docker-compose.demo.yml exec -T backend python manage.py seed_demo_marketing
curl -s -o /dev/null -w 'demo:%{http_code}\n' http://127.0.0.1:8081/demo
curl -s -o /dev/null -w 'health:%{http_code}\n' http://127.0.0.1:8081/api/health/
echo "Listo. Abrí http://dsachubut.sytes.net:8081/demo (NAT 8081 requerido)."
EOF
