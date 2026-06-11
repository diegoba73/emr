#!/usr/bin/env bash
# PROD-5-A — Verificación no destructiva post-restore (staging drill).
# No restaura datos. No modifica producción.
set -euo pipefail

if [[ "${CONFIRM_DRILL_VERIFY:-}" != "true" ]]; then
  echo "ERROR: CONFIRM_DRILL_VERIFY=true es obligatorio." >&2
  exit 1
fi

: "${RESTORE_TARGET_DB:?RESTORE_TARGET_DB requerido — base staging}"
: "${PGHOST:?PGHOST requerido}"
: "${PGPORT:?PGPORT requerido}"
: "${PGUSER:?PGUSER requerido}"

if [[ "${RESTORE_TARGET_DB}" == "synesis_db" ]] && [[ "${ALLOW_RESTORE_PRODUCTION_NAME:-}" != "true" ]]; then
  echo "ERROR: RESTORE_TARGET_DB=synesis_db bloqueado para verificación de drill." >&2
  exit 1
fi

if [[ -n "${BACKUP_FILE:-}" ]]; then
  if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: BACKUP_FILE no encontrado." >&2
    exit 1
  fi
  if [[ -f "${BACKUP_FILE}.sha256" ]]; then
    sha256sum -c "${BACKUP_FILE}.sha256"
    echo "Checksum backup DB: OK"
  else
    echo "AVISO: sin ${BACKUP_FILE}.sha256; omitiendo verificación checksum." >&2
  fi
fi

if [[ -n "${MEDIA_RESTORE_DIR:-}" ]]; then
  if [[ ! -d "${MEDIA_RESTORE_DIR}" ]]; then
    echo "ERROR: MEDIA_RESTORE_DIR no es directorio existente." >&2
    exit 1
  fi
  case "${MEDIA_RESTORE_DIR}" in
    /var/www/*|/usr/share/nginx/*|/srv/www/*)
      echo "ERROR: MEDIA_RESTORE_DIR parece ruta pública web." >&2
      exit 1
      ;;
  esac
  echo "Media restore dir presente (sin listar contenido)."
fi

if command -v psql >/dev/null 2>&1; then
  echo "Conteos agregados (sin PHI):"
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${RESTORE_TARGET_DB}" -v ON_ERROR_STOP=1 -t -A <<'SQL'
SELECT 'pacientes_paciente=' || COUNT(*)::text FROM pacientes_paciente;
SELECT 'laboratorio_solicitudexamen=' || COUNT(*)::text FROM laboratorio_solicitudexamen;
SELECT 'laboratorio_resultadoexamen=' || COUNT(*)::text FROM laboratorio_resultadoexamen;
SQL
else
  echo "AVISO: psql no disponible; omitiendo conteos." >&2
fi

if [[ -n "${RUN_DJANGO_CHECK:-}" ]] && [[ "${RUN_DJANGO_CHECK}" == "true" ]]; then
  if [[ -z "${DJANGO_SETTINGS_MODULE:-}" ]]; then
    echo "ERROR: RUN_DJANGO_CHECK=true requiere DJANGO_SETTINGS_MODULE." >&2
    exit 1
  fi
  if ! command -v python >/dev/null 2>&1; then
    echo "ERROR: python no encontrado para manage.py check." >&2
    exit 1
  fi
  # Operador debe exportar DB_* apuntando a staging antes de invocar.
  python manage.py check
  echo "manage.py check: OK"
fi

echo "Verificación drill completada (no destructiva)."
