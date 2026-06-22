#!/usr/bin/env bash
# Restore local PostgreSQL SYNESIS — por defecto en base de PRUEBA, no productiva.
# Uso: bash scripts/restore_postgres_local.sh /ruta/al/archivo.dump
# Variables opcionales: TARGET_DB PGHOST PGPORT PGUSER DB_USER
# Usuario PostgreSQL: PGUSER (estándar) o DB_USER (alias Django). Si ambos, gana PGUSER.
# Restaurar sobre synesis_db requiere: CONFIRM_RESTORE_PROD=YES_I_UNDERSTAND

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <archivo.dump>" >&2
  echo "Por defecto restaura en TARGET_DB=synesis_restore_test (base de prueba)." >&2
  exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${TARGET_DB:-synesis_restore_test}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-${DB_USER:-synesis_user}}"
PROD_DB_NAME="${PROD_DB_NAME:-synesis_db}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "ERROR: archivo de backup no encontrado: ${BACKUP_FILE}" >&2
  exit 1
fi

# Bloquear restore sobre base productiva típica sin confirmación fuerte.
if [[ "${TARGET_DB}" == "${PROD_DB_NAME}" ]]; then
  if [[ "${CONFIRM_RESTORE_PROD:-}" != "YES_I_UNDERSTAND" ]]; then
    echo "ERROR: restaurar sobre '${PROD_DB_NAME}' requiere CONFIRM_RESTORE_PROD=YES_I_UNDERSTAND" >&2
    echo "Haga backup previo y use ventana de mantenimiento. Preferir TARGET_DB=synesis_restore_test." >&2
    exit 1
  fi
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "ERROR: pg_restore no encontrado. Instale cliente PostgreSQL." >&2
  exit 1
fi

if [[ -f "${BACKUP_FILE}.sha256" ]] && command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "${BACKUP_FILE}.sha256"
fi

if command -v pg_isready >/dev/null 2>&1; then
  if ! pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL no responde en ${PGHOST}:${PGPORT}." >&2
    exit 1
  fi
fi

# Crear base destino solo si no existe. No ejecuta dropdb.
if ! psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" | grep -q 1; then
  echo "Creando base de destino: ${TARGET_DB}"
  createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TARGET_DB}"
else
  echo "Base destino ya existe: ${TARGET_DB}"
  echo "Si contiene datos previos, pg_restore puede fallar o duplicar objetos."
  echo "Use una base vacía o un nombre distinto (TARGET_DB=...)."
fi

pg_restore \
  --host="${PGHOST}" \
  --port="${PGPORT}" \
  --username="${PGUSER}" \
  --dbname="${TARGET_DB}" \
  --no-owner \
  --no-acl \
  --exit-on-error \
  "${BACKUP_FILE}"

echo "Restore completado en base: ${TARGET_DB}"
echo "Próximos pasos sugeridos:"
echo "  1. Ajustar .env temporalmente a DB_NAME=${TARGET_DB} (solo en entorno de prueba)."
echo "  2. python manage.py check"
echo "  3. Smoke focal: pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q"
echo "  4. Verificar login y rutas críticas con datos sintéticos."
echo "No restaurar sobre la base real sin backup previo y confirmación explícita."
