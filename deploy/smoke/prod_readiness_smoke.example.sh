#!/usr/bin/env bash
# PROD-6 — Smoke remoto no destructivo para entorno productivo CONTROLADO (staging/pilot).
# No ejecutar contra producción clínica activa sin autorización explícita.
# No incluye credenciales reales. Usar solo datos/usuarios sintéticos.
set -euo pipefail

: "${BASE_URL:?BASE_URL requerido — p. ej. https://staging.example.com (sin barra final)}"

BASE_URL="${BASE_URL%/}"

echo "PROD-6 smoke — entorno controlado"
echo "BASE_URL=${BASE_URL}"
echo "AVISO: usar solo staging/pilot con datos sintéticos. No PHI en evidencia."

_http_code() {
  curl -sS -o /dev/null -w '%{http_code}' "$@"
}

_fail() {
  echo "FAIL: $*" >&2
  exit 1
}

_pass() {
  echo "OK: $*"
}

# --- Health (público) ---
code="$(_http_code "${BASE_URL}/api/health/")"
if [[ "$code" != "200" ]]; then
  _fail "health esperado 200, obtuvo ${code}"
fi
_pass "GET /api/health/ → ${code}"

# --- Media bloqueada vía Nginx (si BASE_URL apunta al proxy) ---
media_code="$(_http_code "${BASE_URL}/media/")"
if [[ "$media_code" == "200" ]]; then
  _fail "/media/ respondió 200 — posible exposición pública"
fi
_pass "/media/ no público → ${media_code}"

# --- Endpoints protegidos sin auth ---
for path in \
  "/api/pacientes/" \
  "/api/turnos/" \
  "/api/atenciones/" \
  "/api/lab/solicitudes/" \
  "/api/auditoria/events/"
do
  code="$(_http_code "${BASE_URL}${path}")"
  if [[ "$code" == "200" ]]; then
    _fail "${path} accesible anónimo (200)"
  fi
  _pass "anónimo ${path} → ${code} (no 200)"
done

# --- Auth opcional (credenciales sintéticas vía entorno) ---
if [[ -n "${SMOKE_USERNAME:-}" && -n "${SMOKE_PASSWORD:-}" ]]; then
  login_body="$(mktemp)"
  trap 'rm -f "$login_body"' EXIT
  code="$(curl -sS -o "$login_body" -w '%{http_code}' \
    -X POST "${BASE_URL}/api/auth/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${SMOKE_USERNAME}\",\"password\":\"${SMOKE_PASSWORD}\"}")"
  if [[ "$code" != "200" ]]; then
    _fail "login sintético esperado 200, obtuvo ${code}"
  fi
  _pass "POST /api/auth/login/ → ${code}"
  # No imprimir token completo
  if grep -q 'access' "$login_body" 2>/dev/null; then
    _pass "login devolvió token (contenido omitido)"
  fi
  rm -f "$login_body"
  trap - EXIT
else
  echo "SKIP: login (definir SMOKE_USERNAME y SMOKE_PASSWORD para prueba autenticada)"
fi

echo "Smoke PROD-6 completado (no destructivo)."
