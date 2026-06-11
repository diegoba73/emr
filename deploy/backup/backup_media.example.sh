#!/usr/bin/env bash
# PROD-5 — Backup de media clínica privada (plantilla; no commitear archivos generados).
# Uso: export BACKUP_DIR MEDIA_ROOT; ./backup_media.example.sh
set -euo pipefail

: "${BACKUP_DIR:?BACKUP_DIR requerido — directorio de salida fuera del repo}"
: "${MEDIA_ROOT:?MEDIA_ROOT requerido — ruta al volumen media del backend}"

if [[ ! -d "${MEDIA_ROOT}" ]]; then
  echo "ERROR: MEDIA_ROOT no es un directorio existente." >&2
  exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
  echo "ERROR: tar no encontrado en PATH." >&2
  exit 1
fi

TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
mkdir -p "${BACKUP_DIR}"

ARCHIVE="${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz"
MEDIA_PARENT="$(cd "$(dirname "${MEDIA_ROOT}")" && pwd)"
MEDIA_BASENAME="$(basename "${MEDIA_ROOT}")"

tar -czf "${ARCHIVE}" -C "${MEDIA_PARENT}" "${MEDIA_BASENAME}"
sha256sum "${ARCHIVE}" | tee "${ARCHIVE}.sha256"
echo "Backup media completado."
