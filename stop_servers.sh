#!/bin/bash

# ===============================
# Script para detener EMR
# ===============================

echo "🛑 Deteniendo servicios del EMR..."

# ===============================
# Django
# ===============================
echo "🐍 Deteniendo Django..."
pkill -f "manage.py runserver" 2>/dev/null
lsof -ti :8000 | xargs kill -9 2>/dev/null

# ===============================
# React
# ===============================
echo "⚛️  Deteniendo React..."
pkill -f "react-scripts start" 2>/dev/null
lsof -ti :3000 | xargs kill -9 2>/dev/null

sleep 2

# ===============================
# Verificación
# ===============================
echo ""
echo "📊 Verificando puertos..."
if lsof -i :8000 -i :3000 2>/dev/null | grep -q LISTEN; then
    echo "⚠️  Aún hay procesos activos:"
    lsof -i :8000 -i :3000 | grep LISTEN
else
    echo "✅ Puertos 8000 y 3000 liberados correctamente."
fi

echo ""
echo "🧹 EMR detenido."
