#!/usr/bin/env bash
# Deja el APK de pacientes en URL fija y persistente (sobrevive regenerar nginx).
#
# Ejecutar EN EL SERVIDOR de producción (/srv/emr/app), no en la PC de desarrollo:
#   bash scripts/ensure_movil_apk_persistente.sh [/ruta/al.apk]
#
# URL fija (no cambiar; el QR del login ya apunta acá):
#   https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk
#
# Qué hace:
#   1) Publica el APK en /srv/emr/public/synesis-movil.apk (disco del host).
#   2) Verifica montaje del volumen en el contenedor nginx.
#   3) Inserta el location exacto en la conf nginx montada si falta.
#   4) Recarga nginx y prueba el Content-Type.
set -euo pipefail
umask 022

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APK_SRC="${1:-}"
DEST_DIR=/srv/emr/public
DEST_FILE="$DEST_DIR/synesis-movil.apk"
SNIPPET="$ROOT/deploy/nginx/synesis-movil-apk.snippet.conf"
PUBLIC_URL='https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk'
NGINX_CANDIDATES=(emr_nginx_server emr_nginx_prod)
MARKER='location = /synesis-movil.apk'

if [[ ! -f "$SNIPPET" ]]; then
  echo "Falta $SNIPPET (¿estás en /srv/emr/app con el repo actualizado?)." >&2
  exit 1
fi

# --- 1) Publicar APK en host ---
if [[ -n "$APK_SRC" ]]; then
  bash "$ROOT/scripts/publish_movil_apk.sh" "$APK_SRC"
elif [[ -f "$DEST_FILE" ]]; then
  echo "APK ya presente: $DEST_FILE ($(du -h "$DEST_FILE" | awk '{print $1}'))"
else
  echo "No hay APK en $DEST_FILE." >&2
  echo "Uso: $0 /ruta/al/app-release.apk" >&2
  exit 1
fi

# --- 2) Contenedor nginx ---
NGINX_CTR=""
for name in "${NGINX_CANDIDATES[@]}"; do
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$name"; then
    NGINX_CTR="$name"
    break
  fi
done
if [[ -z "$NGINX_CTR" ]]; then
  echo "No se encontró contenedor nginx (${NGINX_CANDIDATES[*]})." >&2
  exit 1
fi
echo "Nginx: $NGINX_CTR"

# --- 3) Volumen host → contenedor ---
if ! docker exec "$NGINX_CTR" test -f /srv/emr/public/synesis-movil.apk 2>/dev/null; then
  echo "AVISO: $NGINX_CTR no ve $DEST_FILE."
  echo "Agregá al servicio nginx de docker-compose.server.yml:"
  echo "  volumes:"
  echo "    - /srv/emr/public:/srv/emr/public:ro"
  echo "Luego: docker compose -f docker-compose.server.yml up -d nginx"
  echo "Reejecutá este script después del recreate."
  exit 2
fi
echo "OK: volumen /srv/emr/public visible en $NGINX_CTR"

# --- 4) Location en conf nginx montada ---
# Buscar el archivo de conf del server block clínico dentro del contenedor.
CONF_CANDIDATES=(
  /etc/nginx/conf.d/default.conf
  /etc/nginx/conf.d/emr.conf
  /etc/nginx/nginx.conf
)
CONF_IN_CTR=""
for c in "${CONF_CANDIDATES[@]}"; do
  if docker exec "$NGINX_CTR" test -f "$c" 2>/dev/null; then
    if docker exec "$NGINX_CTR" grep -q 'server_name\|listen' "$c" 2>/dev/null; then
      CONF_IN_CTR="$c"
      break
    fi
  fi
done
if [[ -z "$CONF_IN_CTR" ]]; then
  echo "No se encontró conf nginx editable en el contenedor." >&2
  exit 1
fi

# Resolver ruta real en el host (bind mount) para editar con backup.
CONF_HOST="$(docker inspect "$NGINX_CTR" --format '{{range .Mounts}}{{println .Destination "->" .Source}}{{end}}' \
  | awk -v dest="$CONF_IN_CTR" '$1==dest {print $3; exit}')"
if [[ -z "$CONF_HOST" || ! -f "$CONF_HOST" ]]; then
  # A veces el mount es un directorio conf.d
  CONF_DIR_HOST="$(docker inspect "$NGINX_CTR" --format '{{range .Mounts}}{{println .Destination "->" .Source}}{{end}}' \
    | awk '$1=="/etc/nginx/conf.d" {print $3; exit}')"
  if [[ -n "$CONF_DIR_HOST" && -f "$CONF_DIR_HOST/$(basename "$CONF_IN_CTR")" ]]; then
    CONF_HOST="$CONF_DIR_HOST/$(basename "$CONF_IN_CTR")"
  fi
fi

if docker exec "$NGINX_CTR" grep -Fq "$MARKER" "$CONF_IN_CTR" 2>/dev/null; then
  echo "OK: ya existe $MARKER en $CONF_IN_CTR"
else
  if [[ -z "$CONF_HOST" || ! -f "$CONF_HOST" ]]; then
    echo "Falta $MARKER y no pude resolver la conf en el host ($CONF_IN_CTR)." >&2
    echo "Insertá a mano el contenido de $SNIPPET dentro del server { ... } clínico." >&2
    exit 3
  fi
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="${CONF_HOST}.bak-apk-${stamp}"
  sudo cp -a "$CONF_HOST" "$backup"
  echo "Backup conf: $backup"
  # Insertar el snippet justo antes del primer "location /" o al final del server.
  if grep -q 'location /' "$CONF_HOST"; then
    # Insertar antes del primer location /
    tmp="$(mktemp)"
    awk -v snippet_file="$SNIPPET" '
      BEGIN { while ((getline line < snippet_file) > 0) snippet = snippet line "\n"; close(snippet_file) }
      /location \/[[:space:]{]/ && !done {
        print "# --- APK móvil URL fija (insertado por ensure_movil_apk_persistente.sh) ---"
        printf "%s", snippet
        done=1
      }
      { print }
    ' "$CONF_HOST" > "$tmp"
    sudo cp "$tmp" "$CONF_HOST"
    rm -f "$tmp"
  else
    echo "No encontré 'location /' en $CONF_HOST; pegá el snippet a mano." >&2
    exit 3
  fi
  echo "Insertado location APK en $CONF_HOST"
fi

# --- 5) Reload + prueba ---
docker exec "$NGINX_CTR" nginx -t
docker exec "$NGINX_CTR" nginx -s reload
echo "Nginx recargado."

echo "Probar:"
echo "  curl -sSI '$PUBLIC_URL' | head -15"
echo "Esperado: HTTP 200 y Content-Type application/vnd.android.package-archive"
curl -sSI "$PUBLIC_URL" | head -15 || true
