#!/usr/bin/env bash
# Publica el APK de pacientes en la URL fija del dominio clínico.
# El archivo queda en disco del host (/srv/emr/public), no dentro del
# contenedor nginx — así sobrevive regeneraciones / redeploys.
#
# Uso:
#   bash scripts/publish_movil_apk.sh /ruta/al/synesis.apk
#
# URL resultante:
#   https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk
set -euo pipefail
umask 022

APK_SRC="${1:-}"
DEST_DIR=/srv/emr/public
DEST_FILE="$DEST_DIR/synesis-movil.apk"
NGINX_SNIPPET_HINT="deploy/nginx/synesis-movil-apk.snippet.conf"
# Nombres habituales del contenedor nginx clínico en este host.
NGINX_CANDIDATES=(emr_nginx_server emr_nginx_prod)

if [[ -z "$APK_SRC" || ! -f "$APK_SRC" ]]; then
  echo "Uso: $0 /ruta/al/archivo.apk" >&2
  exit 1
fi

# Validación mínima de APK (ZIP / PK header).
if ! head -c 2 "$APK_SRC" | grep -q PK; then
  echo "El archivo no parece un APK/ZIP válido." >&2
  exit 1
fi

sudo mkdir -p "$DEST_DIR"
sudo cp -f "$APK_SRC" "$DEST_FILE"
sudo chmod 644 "$DEST_FILE"
sudo chown root:root "$DEST_FILE" 2>/dev/null || true

echo "APK publicado (persistente): $DEST_FILE ($(du -h "$DEST_FILE" | awk '{print $1}'))"
echo "Comprobar nginx: location = /synesis-movil.apk → alias $DEST_FILE"
echo "  (ver $NGINX_SNIPPET_HINT; montar $DEST_DIR en el contenedor nginx)"

if command -v nginx >/dev/null 2>&1; then
  if sudo nginx -t 2>/dev/null; then
    sudo nginx -s reload 2>/dev/null || sudo systemctl reload nginx 2>/dev/null || true
  fi
fi

NGINX_CTR=""
if command -v docker >/dev/null 2>&1; then
  for name in "${NGINX_CANDIDATES[@]}"; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$name"; then
      NGINX_CTR="$name"
      break
    fi
  done
fi

if [[ -n "$NGINX_CTR" ]]; then
  # Si el volumen está montado, el archivo del host ya es visible.
  # Si no, avisamos (no usamos docker cp como destino “oficial”: se pierde al recrear).
  if docker exec "$NGINX_CTR" test -f /srv/emr/public/synesis-movil.apk 2>/dev/null; then
    echo "OK: $NGINX_CTR ve $DEST_FILE vía montaje."
  else
    echo "AVISO: $NGINX_CTR NO ve /srv/emr/public/synesis-movil.apk."
    echo "  Agregá al servicio nginx del compose:"
    echo "    volumes:"
    echo "      - /srv/emr/public:/srv/emr/public:ro"
    echo "  e incluí el location de $NGINX_SNIPPET_HINT. Luego:"
    echo "    docker compose … up -d nginx"
  fi
  docker exec "$NGINX_CTR" nginx -t && docker exec "$NGINX_CTR" nginx -s reload
  echo "Nginx del contenedor $NGINX_CTR recargado."
fi

echo "Probar: curl -sSI 'https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk' | head -15"
