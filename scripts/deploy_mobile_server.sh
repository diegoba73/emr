#!/usr/bin/env bash
# Ejecutar en /srv/emr/app DESPUÉS de integrar el commit desde GitHub.
# Conserva el proyecto Compose, redes y volúmenes existentes. Nunca ejecuta seed.
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for required in docker-compose.server.yml .env.server docker-compose.mobile.server.yml; do
  test -f "$required" || { echo "Falta $required. No se modificó el servidor." >&2; exit 1; }
done
project=$(docker inspect emr_backend_server --format '{{index .Config.Labels "com.docker.compose.project"}}')
service=$(docker inspect emr_backend_server --format '{{index .Config.Labels "com.docker.compose.service"}}')
test -n "$project" && test "$service" = backend || { echo 'No se reconoce el stack clínico.' >&2; exit 1; }
for container in emr_nginx_server emr_postgres_server; do
  actual=$(docker inspect "$container" --format '{{index .Config.Labels "com.docker.compose.project"}}')
  test "$actual" = "$project" || { echo 'Los contenedores pertenecen a proyectos distintos.' >&2; exit 1; }
done
compose=(docker compose -p "$project" --env-file .env.server -f docker-compose.server.yml -f docker-compose.mobile.server.yml)
"${compose[@]}" config --services
backup_dir=/srv/emr/backups
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
release_stamp=$(date -u +%Y%m%dT%H%M%SZ)
release_dir="$backup_dir/mobile-$release_stamp"
mkdir "$release_dir"
# Guardar configuración y referencias para recuperación; archivos privados fuera de Git.
cp .env.server docker-compose.server.yml "$release_dir/"
git rev-parse HEAD > "$release_dir/commit.txt"
docker inspect emr_backend_server emr_nginx_server --format '{{.Name}} {{.Image}}' > "$release_dir/images.txt"
# Leer usuario/base efectivos de Django, no asumir los valores iniciales de Postgres.
docker exec emr_backend_server python -c 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE","synesis.settings"); import django; django.setup(); from django.conf import settings; d=settings.DATABASES["default"]; assert "postgresql" in d["ENGINE"]; print(d["NAME"]); print(d["USER"])' > "$release_dir/database.txt"
mapfile -t database < "$release_dir/database.txt"
test "${#database[@]}" = 2 || { echo 'No se pudo identificar la base efectiva.' >&2; exit 1; }
echo 'Construyendo backend y frontend antes de cambiar los contenedores activos…'
"${compose[@]}" build backend nginx
echo 'Respaldando PostgreSQL…'
docker exec emr_postgres_server pg_dump -U "${database[1]}" -d "${database[0]}" --format=custom > "$release_dir/database.dump"
test -s "$release_dir/database.dump"
docker exec -i emr_postgres_server pg_restore --list < "$release_dir/database.dump" > "$release_dir/database.contents.txt"
sha256sum "$release_dir/database.dump" > "$release_dir/database.dump.sha256"
echo "Respaldo validado en $release_dir"
# Omitir entrypoint de arranque para no iniciar un servidor ni ejecutar seed en el job.
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py check
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --noinput
"${compose[@]}" up -d --no-deps --no-build backend nginx
docker exec emr_backend_server python manage.py check
docker exec emr_backend_server python manage.py showmigrations movil medicos turnos
echo 'Backend actualizado. Verificar HTTPS y ejecutar npm run check:production antes del APK.'
echo "Respaldo y referencias: $release_dir"
