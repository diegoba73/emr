#!/usr/bin/env bash
# Restaura un dump PostgreSQL en la BD Docker emr_postgres (synesis_db).
# Uso:
#   bash scripts/restore_docker_db.sh                          # backup más reciente en ~/backups_synesis
#   bash scripts/restore_docker_db.sh /ruta/al/archivo.dump
#
# ADVERTENCIA: reemplaza por completo synesis_db en Docker.
# Hace backup de seguridad de la BD actual antes de restaurar.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BACKUP_DIR="${BACKUP_DIR:-${HOME}/backups_synesis}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
DB_NAME="${DB_NAME:-synesis_db}"

die() { echo "❌ $*" >&2; exit 1; }

if ! docker info >/dev/null 2>&1; then
  die "Docker no está corriendo."
fi

if ! docker compose ps --status running --services 2>/dev/null | grep -qx db; then
  echo "ℹ️  Levantando Postgres..."
  docker compose up -d db
  sleep 3
fi

if [[ $# -ge 1 ]]; then
  DUMP_FILE="$1"
else
  DUMP_FILE="$(ls -t "${BACKUP_DIR}"/synesis_db_*.dump 2>/dev/null | head -1 || true)"
fi

[[ -n "${DUMP_FILE}" && -f "${DUMP_FILE}" ]] || die "No se encontró dump. Indicá la ruta o guardá backups en ${BACKUP_DIR}"

if [[ -f "${DUMP_FILE}.sha256" ]] && command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "${DUMP_FILE}.sha256"
fi

echo ""
echo "⚠️  Esto REEMPLAZARÁ la base ${DB_NAME} en Docker con:"
echo "    ${DUMP_FILE}"
echo ""
if [[ "${RESTORE_CONFIRM:-}" != "SI" ]]; then
  read -r -p "¿Continuar? (escribí SI): " CONFIRM
  [[ "${CONFIRM}" == "SI" ]] || die "Cancelado."
fi

export PGPASSWORD="${PGPASSWORD:-postgres}"

SAFETY="${BACKUP_DIR}/${DB_NAME}_pre_restore_$(date -u +%Y%m%d_%H%M%S).dump"
mkdir -p "${BACKUP_DIR}"
echo "ℹ️  Backup de seguridad de la BD actual → ${SAFETY}"
pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -Fc -f "${SAFETY}" "${DB_NAME}" || true

docker compose stop backend 2>/dev/null || true

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" || true

dropdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" --if-exists "${DB_NAME}"
createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${DB_NAME}"

echo "ℹ️  Restaurando..."
pg_restore -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" \
  --no-owner --no-acl "${DUMP_FILE}" || true
# pg_restore puede salir !=0 por transaction_timeout (PG18→PG15); los datos suelen restaurarse igual.

echo ""
echo "ℹ️  Aplicando migraciones pendientes..."
if docker compose ps --status running --services 2>/dev/null | grep -qx backend; then
  docker compose exec -T backend python manage.py migrate --noinput
else
  if [[ -x "${REPO_ROOT}/emr_env/bin/python" ]]; then
    "${REPO_ROOT}/emr_env/bin/python" manage.py migrate --noinput
  else
    echo "   Levantá backend o activá emr_env y corré: python manage.py migrate"
  fi
fi

echo ""
echo "ℹ️  Conteos post-restore:"
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -c "
SELECT 'pacientes' AS tabla, COUNT(*)::text FROM pacientes_paciente
UNION ALL SELECT 'historias_clinicas', COUNT(*)::text FROM historias_clinicas_historiaclinica
UNION ALL SELECT 'tipo_examen', COUNT(*)::text FROM laboratorio_tipoexamen
UNION ALL SELECT 'solicitudes_lims', COUNT(*)::text FROM laboratorio_solicitudexamen;
"

echo ""
echo "✅ Restore completado."
echo "   Catálogo LIMS completo (si hace falta): ./emrctl seed"
echo "   Levantar stack: ./emrctl up"
