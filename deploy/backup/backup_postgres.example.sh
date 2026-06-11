#!/usr/bin/env bash
# PROD-5 — Backup lógico PostgreSQL (plantilla operativa; no commitear salidas).
# Uso: export BACKUP_DIR PGHOST PGPORT PGUSER PGDATABASE [PGPASSWORD]; ./backup_postgres.example.sh
set -euo pipefail

: "${BACKUP_DIR:?BACKUP_DIR requerido — directorio de salida fuera del repo}"
: "${PGHOST:?PGHOST requerido}"
: "${PGPORT:?PGPORT requerido}"
: "${PGUSER:?PGUSER requerido}"
: "${PGDATABASE:?PGDATABASE requerido}"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump no encontrado en PATH." >&2
  exit 1
fi

TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/postgres_${TIMESTAMP}.dump"

# PGPASSWORD puede venir del entorno; nunca imprimir credenciales ni DATABASE_URL.
pg_dump \
  --host="${PGHOST}" \
  --port="${PGPORT}" \
  --username="${PGUSER}" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="${BACKUP_FILE}" \
  "${PGDATABASE}"

sha256sum "${BACKUP_FILE}" | tee "${BACKUP_FILE}.sha256"
echo "Backup PostgreSQL completado."
