#!/usr/bin/env bash
# Detener stack EMR (Docker + procesos locales huérfanos).

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🛑 Deteniendo EMR..."

if [ -x "$BASE_DIR/emrctl" ]; then
  "$BASE_DIR/emrctl" down
else
  pkill -f "manage.py runserver" 2>/dev/null || true
  pkill -f "react-scripts start" 2>/dev/null || true
  lsof -ti :8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  lsof -ti :3000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  echo "✅ Procesos locales detenidos."
fi
