#!/usr/bin/env bash
# Verifica que el entorno local use la BD única Docker (emr_postgres / synesis_db).
# Sale con código 1 si la configuración es insegura o inconsistente.
#
# Uso: bash scripts/verify_local_db.sh
# Lo invoca emrctl automáticamente antes de levantar servicios.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

ENV_FILE="${REPO_ROOT}/.env"
ERR=0

fail() {
  echo "❌ $*" >&2
  ERR=1
}

warn() {
  echo "⚠️  $*" >&2
}

# --- .env: credenciales prohibidas ---
if [[ -f "${ENV_FILE}" ]]; then
  if grep -qE '^[[:space:]]*DB_USER=synesis_user' "${ENV_FILE}"; then
    fail "DB_USER=synesis_user en .env está PROHIBIDO. Usá postgres (docker-compose.yml)."
  fi
  if grep -qE '^[[:space:]]*DB_NAME=' "${ENV_FILE}"; then
    db_name="$(grep -E '^[[:space:]]*DB_NAME=' "${ENV_FILE}" | tail -1 | cut -d= -f2- | tr -d ' \"')"
    if [[ -n "${db_name}" && "${db_name}" != "synesis_db" ]]; then
      fail "DB_NAME=${db_name} no coincide con la BD única local (synesis_db)."
    fi
  fi
else
  warn "No existe .env — copiá .env.example antes de trabajar."
fi

# --- Docker corriendo ---
if ! docker info >/dev/null 2>&1; then
  fail "Docker no está corriendo. La BD local vive en emr_postgres."
else
  if ! docker compose ps --status running --services 2>/dev/null | grep -qx db; then
    fail "Contenedor emr_postgres no está activo. Ejecutá: ./emrctl up"
  fi
fi

# --- Postgres responde ---
if command -v pg_isready >/dev/null 2>&1; then
  if ! pg_isready -h localhost -p 5432 -U postgres >/dev/null 2>&1; then
    fail "PostgreSQL no responde en localhost:5432 (¿emr_postgres levantado?)."
  fi
fi

if [[ "${ERR}" -ne 0 ]]; then
  echo "" >&2
  echo "Referencia: docs/dev-start.md — una sola BD: Docker emr_postgres → synesis_db" >&2
  exit 1
fi

echo "✅ BD local verificada: emr_postgres / synesis_db (postgres@localhost:5432)"
