#!/usr/bin/env bash
# Diagnóstico local EMR (solo lectura; no modifica DB ni procesos).

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$BASE_DIR/frontend"
LOG_DIR="$BASE_DIR/logs"
PYTHON="$BASE_DIR/emr_env/bin/python"

echo "🔍 Diagnóstico del sistema EMR"
echo "================================"
echo "   Repo: $BASE_DIR"
echo ""

# --- Python / Django ---
echo "1️⃣  Python / Django"
echo "-------------------"
if [ -x "$PYTHON" ]; then
  echo "   ✅ $PYTHON"
  "$PYTHON" --version | sed 's/^/      /'
  if "$PYTHON" -c "import django; print('Django', django.get_version())" 2>/dev/null; then
    echo "   ✅ Django importable"
  else
    echo "   ❌ Django no importable en emr_env"
  fi
else
  echo "   ❌ No existe: $PYTHON"
fi

if [ -f "$BASE_DIR/manage.py" ]; then
  echo "   ✅ manage.py"
else
  echo "   ❌ manage.py no encontrado"
fi

if [ -f "$BASE_DIR/requirements.txt" ]; then
  echo "   ✅ requirements.txt"
else
  echo "   ⚠️  requirements.txt no encontrado"
fi

if [ -f "$BASE_DIR/pytest.ini" ]; then
  echo "   ✅ pytest.ini"
else
  echo "   ⚠️  pytest.ini no encontrado"
fi

# --- Node ---
echo ""
echo "2️⃣  Node / npm / npx"
echo "--------------------"
for cmd in node npm npx; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "   ✅ $cmd: $($cmd --version 2>/dev/null | head -1) ($(command -v "$cmd"))"
  else
    echo "   ❌ $cmd no está en PATH"
    if [ "$cmd" = "node" ] && [ -d "$HOME/.nvm" ]; then
      echo "      💡 Probá: export NVM_DIR=\"\$HOME/.nvm\" && . \"\$NVM_DIR/nvm.sh\""
    fi
  fi
done

if [ -f "$FRONTEND_DIR/package.json" ]; then
  echo "   ✅ frontend/package.json"
else
  echo "   ❌ frontend/package.json no encontrado"
fi

if [ -d "$FRONTEND_DIR/node_modules" ]; then
  echo "   ✅ frontend/node_modules"
else
  echo "   ❌ frontend/node_modules ausente (sugerido: cd frontend && npm install)"
fi

# --- Docker ---
echo ""
echo "3️⃣  Docker / Compose"
echo "--------------------"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    echo "   ✅ docker daemon activo"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^emr_postgres$'; then
      echo "   ✅ contenedor emr_postgres en ejecución"
    else
      echo "   ⚠️  contenedor emr_postgres no está corriendo"
    fi
  else
    echo "   ⚠️  docker instalado pero daemon no responde"
  fi
else
  echo "   ❌ docker no encontrado en PATH"
fi

if docker compose version >/dev/null 2>&1; then
  echo "   ✅ docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  echo "   ✅ docker-compose (legacy)"
else
  echo "   ⚠️  docker compose no disponible"
fi

# --- Puertos ---
echo ""
echo "4️⃣  Puertos 5432 / 8000 / 3000"
echo "------------------------------"
for port in 5432 8000 3000; do
  if lsof -i ":$port" >/dev/null 2>&1; then
    echo "   ⚠️  :$port en uso:"
    lsof -i ":$port" 2>/dev/null | grep LISTEN | sed 's/^/      /' || true
  else
    echo "   ✅ :$port libre"
  fi
done

# --- Logs ---
echo ""
echo "5️⃣  Logs"
echo "--------"
for log in backend.log frontend.log; do
  path="$LOG_DIR/$log"
  if [ -f "$path" ]; then
    echo "   ✅ $path (últimas 3 líneas):"
    tail -n 3 "$path" 2>/dev/null | sed 's/^/      /' || true
  else
    echo "   ℹ️  $path no existe aún"
  fi
done

# --- HTTP (solo lectura) ---
echo ""
echo "6️⃣  HTTP local (lectura)"
echo "-------------------------"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/ 2>/dev/null | grep -qE '200|301|302|403'; then
  echo "   ✅ Backend responde en http://localhost:8000"
else
  echo "   ℹ️  Backend no responde en http://localhost:8000"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -qE '200|301|302'; then
  echo "   ✅ Frontend responde en http://localhost:3000"
else
  echo "   ℹ️  Frontend no responde en http://localhost:3000"
fi

# --- Postgres (conectividad) ---
echo ""
echo "7️⃣  PostgreSQL"
echo "-------------"
if command -v pg_isready >/dev/null 2>&1; then
  if pg_isready -h 127.0.0.1 -p 5432 -q 2>/dev/null; then
    echo "   ✅ pg_isready: Postgres acepta conexiones en 127.0.0.1:5432"
  else
    echo "   ⚠️  pg_isready: Postgres no responde en 127.0.0.1:5432"
    echo "      💡 START_DB=true ./emr-start  o  docker compose up -d db"
  fi
elif lsof -i :5432 >/dev/null 2>&1; then
  echo "   ⚠️  :5432 en uso pero pg_isready no está instalado (no se pudo verificar readiness)"
else
  echo "   ❌ :5432 sin servicio (levantá Postgres antes de ./emr-start)"
  echo "      💡 START_DB=true ./emr-start"
fi

echo ""
echo "================================"
echo "✅ Diagnóstico completado (sin cambios aplicados)"
echo ""
echo "Guía de arranque: docs/dev-start.md"
echo ""
echo "Comandos sugeridos (no ejecutados automáticamente):"
echo "  ./emr_env/bin/python manage.py check"
echo "  ./emr_env/bin/pytest laboratorio/tests/test_api.py -q --reuse-db"
echo "  START_DB=true ./emr-start"
echo "  RUN_SEED=true ./emr-start"
echo "  ./stop_servers.sh"
