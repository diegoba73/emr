#!/usr/bin/env bash
# Ejecutar después de incorporar origin/master; ver docs/despliegue-20260924.md.
set -euo pipefail
umask 077
cd /srv/emr/app
for archivo in .env.server docker-compose.server.yml Dockerfile.server docs/Catalogo_reactivos.csv; do
  test -f "$archivo" || { echo "Falta $archivo" >&2; exit 1; }
done
respaldo="/srv/emr/respaldo-20260924-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$respaldo"
git rev-parse HEAD > "$respaldo/commit-nuevo.txt"
cp -p .env.server docker-compose.server.yml Dockerfile.server "$respaldo/"
cat > docker-compose.actualizacion-runtime.yml <<'YAML'
services:
  backend:
    environment:
      RUN_MIGRATIONS: "false"
      RUN_SEED: "false"
YAML
compose=(docker compose --env-file .env.server -f docker-compose.server.yml -f docker-compose.actualizacion-runtime.yml)
"${compose[@]}" config --quiet
for servicio in backend nginx; do
  docker inspect "emr_${servicio}_server" > "$respaldo/${servicio}-inspect.json"
  docker export --output="$respaldo/${servicio}-rootfs.tar" "emr_${servicio}_server"
  tar -tf "$respaldo/${servicio}-rootfs.tar" > /dev/null
done
"${compose[@]}" build backend nginx
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py check
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --plan
echo "Inicio de ventana de mantenimiento. Respaldo: $respaldo"
trap 'echo "Actualización interrumpida. Revisar el error antes de reabrir el servicio. Respaldo: $respaldo" >&2' ERR
"${compose[@]}" stop nginx backend
docker exec emr_postgres_server sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$respaldo/postgres.dump"
test -s "$respaldo/postgres.dump"
docker exec -i emr_postgres_server pg_restore --list < "$respaldo/postgres.dump" > "$respaldo/postgres-contenido.txt"
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --noinput
# Montar explícitamente el CSV: funciona aunque Dockerfile.server no copie docs/.
importar=("${compose[@]}" run --rm --no-deps -v "$PWD/docs/Catalogo_reactivos.csv:/tmp/catalogo-reactivos.csv:ro" -v "$respaldo:/respaldo" --entrypoint python backend manage.py import_catalogo_reactivos_csv /tmp/catalogo-reactivos.csv)
"${importar[@]}" --report /respaldo/reactivos-simulacion.json
"${importar[@]}" --apply --report /respaldo/reactivos-aplicado.json
"${importar[@]}" --report /respaldo/reactivos-verificacion.json
python3 - "$respaldo/reactivos-verificacion.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding='utf-8') as stream:
    report = json.load(stream)
if any(p['accion'] != 'sin_cambios' for p in report['productos']):
    raise SystemExit('El catálogo no quedó idempotente; revisar los informes.')
print(f"Catálogo verificado: {len(report['productos'])} productos sin cambios pendientes.")
PY
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py collectstatic --noinput
"${compose[@]}" up -d --no-deps --no-build --pull never --force-recreate backend nginx
"${compose[@]}" exec -T backend python manage.py migrate --check
"${compose[@]}" exec -T backend python manage.py check
"${compose[@]}" ps
echo "Actualización finalizada. Respaldo e informes: $respaldo"
