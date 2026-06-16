#!/usr/bin/env bash
# PROD-10 — Smoke piloto técnico controlado (no destructivo).
# Aplica verificaciones PROD-6 + login autenticado opcional.
# No ejecutar contra producción clínica activa sin autorización explícita.
# Evidencia real: completar PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md FUERA del repo.
set -euo pipefail

: "${BASE_URL:?BASE_URL requerido — p. ej. https://staging-pilot.example.internal (sin barra final)}"

BASE_URL="${BASE_URL%/}"
EVIDENCE_DIR="${EVIDENCE_DIR:-}"

echo "PROD-10 technical pilot smoke — entorno controlado"
echo "BASE_URL=${BASE_URL}"
echo "AVISO: solo staging/pilot con datos sintéticos. No PHI en evidencia."
echo "AVISO: no escribir evidencia en el repo por defecto."

if [[ -n "${EVIDENCE_DIR}" ]]; then
  case "${EVIDENCE_DIR}" in
    *"/emr/"*|*"$(pwd)"*)
      echo "ERROR: EVIDENCE_DIR no debe apuntar dentro del repositorio." >&2
      exit 1
      ;;
  esac
fi

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

_skip() {
  echo "SKIP: $*"
}

# --- Health ---
code="$(_http_code "${BASE_URL}/api/health/")"
if [[ "$code" != "200" ]]; then
  _fail "GET /api/health/ esperado 200, obtuvo ${code}"
fi
_pass "GET /api/health/ → ${code}"

# --- Media no público ---
media_code="$(_http_code "${BASE_URL}/media/")"
if [[ "$media_code" == "200" ]]; then
  _fail "/media/ respondió 200 — posible exposición pública (NO-GO)"
fi
_pass "/media/ no público → ${media_code}"

# --- APIs protegidas anónimas ---
for path in \
  "/api/pacientes/" \
  "/api/turnos/" \
  "/api/atenciones/" \
  "/api/lab/solicitudes/" \
  "/api/auditoria/events/"
do
  code="$(_http_code "${BASE_URL}${path}")"
  if [[ "$code" == "200" ]]; then
    _fail "${path} accesible anónimo (200) — NO-GO seguridad"
  fi
  _pass "anónimo ${path} → ${code} (no 200)"
done

# --- Smoke autenticado (usuario sintético vía entorno) ---
if [[ -n "${SMOKE_USERNAME:-}" && -n "${SMOKE_PASSWORD:-}" ]]; then
  login_body="$(mktemp)"
  trap 'rm -f "$login_body"' EXIT
  code="$(curl -sS -o "$login_body" -w '%{http_code}' \
    -X POST "${BASE_URL}/api/auth/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${SMOKE_USERNAME}\",\"password\":\"${SMOKE_PASSWORD}\"}")"
  if [[ "$code" != "200" ]]; then
    _fail "POST /api/auth/login/ esperado 200, obtuvo ${code}"
  fi
  _pass "POST /api/auth/login/ → ${code}"

  if grep -q 'access' "$login_body" 2>/dev/null; then
    _pass "login devolvió token (contenido omitido)"
    token="$(sed -n 's/.*"access"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$login_body" | head -1)"
    if [[ -n "$token" ]]; then
      cu_code="$(curl -sS -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer ${token}" \
        "${BASE_URL}/api/auth/current-user/")"
      if [[ "$cu_code" != "200" ]]; then
        _fail "GET /api/auth/current-user/ esperado 200, obtuvo ${cu_code}"
      fi
      _pass "GET /api/auth/current-user/ → ${cu_code}"
    else
      _skip "current-user (token no extraíble sin imprimir)"
    fi
  fi
  rm -f "$login_body"
  trap - EXIT
else
  _skip "login autenticado (definir SMOKE_USERNAME y SMOKE_PASSWORD vía entorno)"
fi

# --- Observabilidad complementaria (opcional, mismo host) ---
if command -v docker >/dev/null 2>&1; then
  _skip "observability docker checks — ejecutar deploy/observability/check_observability.example.sh por separado"
else
  _skip "docker no disponible — omitiendo checks locales de contenedores"
fi

echo "PROD-10 technical pilot smoke completado (no destructivo)."
echo "INFO: completar evidencia fuera del repo con PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md"
