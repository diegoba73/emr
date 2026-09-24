# Administración avanzada: despliegue en el servidor EMR

Ejecutar en `server@emr.sytes.net`, SSH **2223**, dentro de `/srv/emr/app`.
Este cambio necesita backend, frontend y la migración `internacion.0008`.
No alcanza con reconstruir nginx. La consola usa `/api/administracion/`, dentro
del proxy `/api/` existente. El usuario ingresa con sus credenciales de administrador.

## 1. Conservar la versión actual

```bash
bash <<'BASH'
set -euo pipefail
cd /srv/emr/app
umask 077
git diff --quiet
git diff --cached --quiet
respaldo="/srv/emr/respaldo-admin-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$respaldo/deploy"
git rev-parse HEAD > "$respaldo/commit.txt"
cp -p .env.server Dockerfile.server docker-compose.server.yml "$respaldo/"
cp -p deploy/frontend-nginx.Dockerfile deploy/nginx.emr.test.conf "$respaldo/deploy/"
for servicio in backend nginx; do
  docker inspect "emr_${servicio}_server" > "$respaldo/${servicio}-inspect.json"
  docker export --output="$respaldo/${servicio}-rootfs.tar" "emr_${servicio}_server"
  tar -tf "$respaldo/${servicio}-rootfs.tar" > /dev/null
done
docker exec emr_postgres_server sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$respaldo/postgres.dump"
test -s "$respaldo/postgres.dump"
docker exec -i emr_postgres_server pg_restore --list < "$respaldo/postgres.dump" > "$respaldo/postgres-contenido.txt"
echo "Respaldo: $respaldo"
BASH
```

Los `rootfs.tar` conservan el código ejecutado, incluso si Docker no puede etiquetar
la imagen original. Los volúmenes media/static no se incluyen en `docker export`;
este despliegue no elimina esos volúmenes. El dump conserva la base. Los respaldos
contienen datos/configuración privada: no subirlos a GitHub ni pegarlos en el chat.

## 2. Incorporar el cambio sin reemplazar la rama del barcode

```bash
cd /srv/emr/app
git fetch origin
git merge --no-edit origin/master
```

Si el merge informa conflictos, resolverlos antes del build. Se conserva la rama
actual y los commits de impresión/lectura de etiquetas. No se usa reset ni limpieza
de archivos de despliegue locales.

## 3. Construir, migrar y recrear los dos servicios

```bash
bash <<'BASH'
set -euo pipefail
cd /srv/emr/app
umask 077
cat > docker-compose.admin-runtime.yml <<'YAML'
services:
  backend:
    environment:
      RUN_MIGRATIONS: "false"
      RUN_SEED: "false"
YAML
compose=(docker compose --env-file .env.server -f docker-compose.server.yml -f docker-compose.admin-runtime.yml)
"${compose[@]}" build backend nginx
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py check
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate internacion 0008_vigencia_infraestructura --plan
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate internacion 0008_vigencia_infraestructura --noinput
"${compose[@]}" run --rm --no-deps --entrypoint python backend manage.py collectstatic --noinput
"${compose[@]}" up -d --no-deps --no-build --pull never --force-recreate backend nginx
"${compose[@]}" ps
"${compose[@]}" exec -T backend python manage.py migrate --check
BASH
```

Usar ambos archivos compose para posteriores recreaciones, manteniendo migraciones
y seeds explícitos. La migración agrega indicadores de vigencia con valor inicial
`true` y protege relaciones: no elimina camas, internaciones ni resultados.

## 4. Comprobar el funcionamiento

- Recargar la aplicación. Con admin, abrir **Administración avanzada** y verificar
  que se ven catálogos, usuarios, camas y los demás módulos. Puede pedir iniciar
  sesión si el navegador no tiene una sesión Django vigente.
- Con otro rol, la opción no aparece y la URL no concede acceso.
- Verificar la ficha e historial de un paciente y la carga de resultados con previos.
- Comprobar impresión y lectura de una etiqueta con el procedimiento habitual.

No retirar registros reales solo para probar. Las pruebas automatizadas cubren
retiro, recuperación y conservación de internaciones en la base de pruebas.
