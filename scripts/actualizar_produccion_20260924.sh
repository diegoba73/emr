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
if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  "${compose[@]}" build backend nginx
fi
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py check
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --plan
# POSTGRES_USER/POSTGRES_DB pueden no existir en el contenedor de PostgreSQL.
# Usar la configuración efectiva de Django, sin leer ni imprimir contraseñas.
db_config=$("${compose[@]}" run --rm --no-deps -T --entrypoint python backend -c '
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "synesis.settings")
from django.conf import settings
db = settings.DATABASES["default"]
values = [db.get("USER"), db.get("NAME")]
if any(not isinstance(v, str) or not v.strip() or "\n" in v or "\r" in v for v in values):
    raise SystemExit("Django debe tener USER y NAME de base explícitos para respaldar.")
print("\n".join(values))')
mapfile -t db_values <<< "$db_config"
[[ ${#db_values[@]} -eq 2 ]] || { echo "Configuración de base inesperada" >&2; exit 1; }
db_user="${db_values[0]}"
db_name="${db_values[1]}"
# Comprobar el mismo acceso que utilizará pg_dump antes de detener servicios.
docker exec emr_postgres_server psql -X -w -U "$db_user" -d "$db_name" -v ON_ERROR_STOP=1 -Atc 'SELECT 1' > /dev/null
echo "Inicio de ventana de mantenimiento. Respaldo: $respaldo"
trap 'echo "Actualización interrumpida. Revisar el error antes de reabrir el servicio. Respaldo: $respaldo" >&2' ERR
"${compose[@]}" stop nginx backend
docker exec emr_postgres_server pg_dump -w -U "$db_user" -d "$db_name" -Fc > "$respaldo/postgres.dump"
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
