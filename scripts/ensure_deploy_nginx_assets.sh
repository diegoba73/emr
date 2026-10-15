#!/usr/bin/env bash
# Asegura en el host de prod los archivos de deploy de nginx que el compose necesita
# y que antes vivían solo en respaldos (se perdían al stash/merge).
#
# Ejecutar EN EL SERVIDOR: cd /srv/emr/app && bash scripts/ensure_deploy_nginx_assets.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need=(
  deploy/frontend-nginx.Dockerfile
  deploy/nginx/nginx.emr.conf
  deploy/nginx.emr.test.conf
  deploy/nginx/synesis-movil-apk.snippet.conf
)
missing=0
for f in "${need[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "FALTA: $f" >&2
    missing=1
  else
    echo "OK: $f"
  fi
done
if [[ "$missing" -ne 0 ]]; then
  echo "Actualizá el repo (git fetch + merge) antes del build." >&2
  exit 1
fi

# Compat: algunos compose antiguos copian deploy/nginx.emr.test.conf
if ! cmp -s deploy/nginx/nginx.emr.conf deploy/nginx.emr.test.conf 2>/dev/null; then
  cp -a deploy/nginx/nginx.emr.conf deploy/nginx.emr.test.conf
  echo "Sincronizado deploy/nginx.emr.test.conf ← nginx.emr.conf"
fi

echo "Listo. Compose nginx debe montar: /srv/emr/public:/srv/emr/public:ro"
echo "Luego: docker compose ... build nginx && up -d --force-recreate nginx"
