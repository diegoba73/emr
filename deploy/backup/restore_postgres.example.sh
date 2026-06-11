#!/usr/bin/env bash
# PROD-5 — Restore PostgreSQL SOLO staging / restore drill.
# NO ejecutar sobre la base productiva activa. Probar primero en entorno aislado.
set -euo pipefail

if [[ "${CONFIRM_RESTORE:-}" != "true" ]]; then
  echo "ERROR: CONFIRM_RESTORE=true es obligatorio para restore." >&2
  exit 1
fi

: "${RESTORE_TARGET_DB:?RESTORE_TARGET_DB requerido — nombre de base vacía o de staging}"
: "${BACKUP_FILE:?BACKUP_FILE requerido — ruta al .dump de pg_dump}"
: "${PGHOST:?PGHOST requerido}"
: "${PGPORT:?PGPORT requerido}"
: "${PGUSER:?PGUSER requerido}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "ERROR: BACKUP_FILE no encontrado." >&2
  exit 1
fi

# Bloqueo por defecto del nombre típico de producción en compose example (forzar target staging).
if [[ "${RESTORE_TARGET_DB}" == "synesis_db" ]] && [[ "${ALLOW_RESTORE_PRODUCTION_NAME:-}" != "true" ]]; then
  echo "ERROR: RESTORE_TARGET_DB=synesis_db bloqueado por defecto." >&2
  echo "Use un nombre de base de staging o ALLOW_RESTORE_PRODUCTION_NAME=true bajo riesgo operativo explícito." >&2
  exit 1
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "ERROR: pg_restore no encontrado en PATH." >&2
  exit 1
fi

if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  sha256sum -c "${BACKUP_FILE}.sha256"
fi

# Sin eliminación destructiva de la base destino. La base debe existir y estar vacía o de drill.
# PGPASSWORD puede venir del entorno; nunca imprimir credenciales.
pg_restore \
  --host="${PGHOST}" \
  --port="${PGPORT}" \
  --username="${PGUSER}" \
  --dbname="${RESTORE_TARGET_DB}" \
  --no-owner \
  --no-acl \
  --exit-on-error \
  "${BACKUP_FILE}"

echo "Restore completado."
