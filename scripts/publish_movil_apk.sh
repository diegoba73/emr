#!/usr/bin/env bash
# Publica el APK de pacientes en la URL fija del dominio clínico.
# Ejecutar en el servidor (o con APK local + SSH).
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

echo "APK publicado: $DEST_FILE ($(du -h "$DEST_FILE" | awk '{print $1}'))"
echo "Comprobar nginx: debe existir location = /synesis-movil.apk (ver $NGINX_SNIPPET_HINT)"
if command -v nginx >/dev/null 2>&1; then
  if sudo nginx -t 2>/dev/null; then
    sudo nginx -s reload 2>/dev/null || sudo systemctl reload nginx 2>/dev/null || true
  fi
fi
# Si nginx corre en Docker (emr_nginx_server), recargar ahí:
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx emr_nginx_server; then
  docker exec emr_nginx_server nginx -t && docker exec emr_nginx_server nginx -s reload
  echo "Nginx del contenedor emr_nginx_server recargado."
fi

echo "Probar: curl -sSI 'https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk' | head -15"
echo
echo "Si nginx (Docker) aún no sirve el archivo:"
echo "  1) Incluí el location de deploy/nginx/synesis-movil-apk.snippet.conf"
echo "     en el server HTTPS :8080 y montá /srv/emr/public en el contenedor."
echo "  2) O, prueba rápida:"
echo "     docker cp $DEST_FILE emr_nginx_server:/usr/share/nginx/html/synesis-movil.apk"
echo "     (requiere location o root que sirva ese path)"
