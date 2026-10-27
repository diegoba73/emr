#!/bin/bash
# Deploy selectivo LIMS (commit en origin/master). NO incluye turnos/recepción.
# Aviso: build nginx/frontend puede tardar 30–90+ min en este host (~3 GB RAM).
# Cortar el build (Ctrl+C) NO tumba los contenedores actuales.
set -euo pipefail

cd /srv/emr/app
umask 077

echo "== tip actual =="
git log -1 --oneline
git rev-parse HEAD | tee /srv/emr/commit-antes-lims-selectivo.txt
git status -sb

echo "== fetch + merge origin/master =="
git fetch origin
git merge --no-edit origin/master

echo "== tip post-merge =="
git log -1 --oneline

COMPOSE=(docker compose -f docker-compose.server.yml)

echo "== build backend (caché) =="
"${COMPOSE[@]}" build backend

echo "== build nginx/frontend (puede 30–90+ min) =="
"${COMPOSE[@]}" build nginx

echo "== recreate backend + nginx =="
"${COMPOSE[@]}" up -d --force-recreate --no-deps backend nginx

echo "== migrate =="
"${COMPOSE[@]}" exec -T backend python manage.py migrate --noinput

echo "== smoke health =="
curl -fsS -o /dev/null -w "health:%{http_code}\n" http://127.0.0.1/api/health/ || \
  curl -fsS -o /dev/null -w "health:%{http_code}\n" http://127.0.0.1:80/api/health/ || true

echo "== tip final =="
git log -1 --oneline
"${COMPOSE[@]}" ps
echo "DEPLOY_LIMS_OK"
