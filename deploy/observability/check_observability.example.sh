#!/usr/bin/env bash
# PROD-9 — Checks de observabilidad mínima (no destructivos).
# No ejecutar contra producción clínica activa sin autorización explícita.
# No imprime secretos, PHI ni contenido de logs clínicos.
set -euo pipefail

: "${BASE_URL:?BASE_URL requerido — p. ej. http://127.0.0.1 (sin barra final)}"

BASE_URL="${BASE_URL%/}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-emr_backend_prod}"
NGINX_CONTAINER="${NGINX_CONTAINER:-emr_nginx_prod}"
DB_CONTAINER="${DB_CONTAINER:-emr_postgres_prod}"

echo "PROD-9 observability check — entorno controlado"
echo "BASE_URL=${BASE_URL}"
echo "AVISO: solo staging/pilot. Evidencia sanitizada fuera del repo."

_pass() { echo "OK: $*"; }
_fail() { echo "FAIL: $*" >&2; exit 1; }
_skip() { echo "SKIP: $*"; }

_http_code() {
  curl -sS -o /dev/null -w '%{http_code}' "$@"
}

# --- Health externo ---
code="$(_http_code "${BASE_URL}/api/health/")"
if [[ "$code" != "200" ]]; then
  _fail "GET /api/health/ esperado 200, obtuvo ${code}"
fi
_pass "GET /api/health/ → ${code}"

# --- Media no público ---
media_code="$(_http_code "${BASE_URL}/media/")"
if [[ "$media_code" == "200" ]]; then
  _fail "/media/ respondió 200 — posible exposición pública"
fi
_pass "/media/ no público → ${media_code}"

# --- API protegida anónima ---
pac_code="$(_http_code "${BASE_URL}/api/pacientes/")"
if [[ "$pac_code" == "200" ]]; then
  _fail "/api/pacientes/ anónimo respondió 200"
fi
_pass "anónimo /api/pacientes/ → ${pac_code} (no 200)"

# --- Contenedores (si Docker disponible) ---
if command -v docker >/dev/null 2>&1; then
  for c in "$BACKEND_CONTAINER" "$NGINX_CONTAINER" "$DB_CONTAINER"; do
    if docker ps --format '{{.Names}}' | grep -qx "$c"; then
      status="$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null || echo unknown)"
      restarts="$(docker inspect --format '{{.RestartCount}}' "$c" 2>/dev/null || echo '?')"
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "$c" 2>/dev/null || echo n/a)"
      echo "CONTAINER ${c}: status=${status} restarts=${restarts} health=${health}"
      if [[ "$status" != "running" ]]; then
        _fail "contenedor ${c} no está running (${status})"
      fi
      _pass "contenedor ${c} running (restarts=${restarts}, health=${health})"
    else
      _skip "contenedor ${c} no encontrado en este host"
    fi
  done

  if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    if docker exec "$DB_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then
      _pass "PostgreSQL pg_isready OK (${DB_CONTAINER})"
    else
      _fail "PostgreSQL pg_isready falló (${DB_CONTAINER})"
    fi
  fi
else
  _skip "docker no disponible — omitiendo checks de contenedores"
fi

# --- Disco (agregado, sin paths sensibles detallados) ---
if command -v df >/dev/null 2>&1; then
  echo "DISK: resumen df -h (porcentajes agregados)"
  df -h 2>/dev/null | awk 'NR==1 || /%$/ {print}' || true
  _pass "df -h ejecutado (revisar manualmente umbrales)"
else
  _skip "df no disponible"
fi

if command -v docker >/dev/null 2>&1; then
  if docker system df >/dev/null 2>&1; then
    echo "DISK: docker system df (resumen)"
    docker system df 2>/dev/null | head -20 || true
    _pass "docker system df ejecutado"
  fi
fi

# --- Backups programados: recordatorio operador ---
echo "INFO: verificar backups programados y artefactos recientes fuera del repo (PROD-5/PROD-7)"
echo "INFO: responsable operativo e incidentes — ver PROD_OBSERVABILITY_MIN.md"

echo "PROD-9 observability check completado (no destructivo)."
