#!/usr/bin/env bash
# Backup local PostgreSQL SYNESIS — salida fuera del repo por defecto.
# Uso: bash scripts/backup_postgres_local.sh
# Variables opcionales: DB_NAME BACKUP_DIR PGHOST PGPORT PGUSER
# PGPASSWORD: solo vía entorno del operador; nunca se imprime.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

DB_NAME="${DB_NAME:-synesis_db}"
BACKUP_DIR="${BACKUP_DIR:-${HOME}/backups_synesis}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump no encontrado. Instale cliente PostgreSQL." >&2
  exit 1
fi

# Evitar escribir dumps dentro del repositorio por defecto.
case "${BACKUP_DIR}" in
  "${REPO_ROOT}"|"${REPO_ROOT}"/*)
    echo "ERROR: BACKUP_DIR no puede estar dentro del repositorio: ${BACKUP_DIR}" >&2
    exit 1
    ;;
esac

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}" 2>/dev/null || true

TIMESTAMP="$(date -u +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"

# Verificación ligera de conectividad (sin imprimir credenciales).
if command -v pg_isready >/dev/null 2>&1; then
  if ! pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL no responde en ${PGHOST}:${PGPORT} (usuario ${PGUSER})." >&2
    exit 1
  fi
fi

pg_dump \
  --host="${PGHOST}" \
  --port="${PGPORT}" \
  --username="${PGUSER}" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="${BACKUP_FILE}" \
  "${DB_NAME}"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"
fi

echo "Backup PostgreSQL completado."
echo "Archivo: ${BACKUP_FILE}"
echo "Base: ${DB_NAME}"
echo "Directorio: ${BACKUP_DIR}"
echo "No subir este archivo a Git. Contiene datos sensibles (PHI/PII)."
