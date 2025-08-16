#!/bin/bash

# Script para iniciar servidores EMR (Versión Corregida)
# Autor: Assistant
# Fecha: $(date)

echo "🚀 Iniciando servidores del proyecto EMR..."
echo "=========================================="

# Verificar si estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Debes ejecutar este script desde el directorio raíz del proyecto EMR"
    echo "   cd /Users/diegobaulde/Downloads/emr"
    exit 1
fi

# Función para verificar si un puerto está en uso
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Puerto $1 ya está en uso"
        return 1
    else
        echo "✅ Puerto $1 disponible"
        return 0
    fi
}

# Función para matar procesos en un puerto
kill_port() {
    echo "🔄 Deteniendo procesos en puerto $1..."
    lsof -ti:$1 | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Verificar y limpiar puertos
echo "🔍 Verificando puertos..."
check_port 8000 && kill_port 8000
check_port 3000 && kill_port 3000

# Activar entorno virtual
echo "🐍 Activando entorno virtual..."
if [ -d "emr_ev" ]; then
    source emr_ev/bin/activate
    echo "✅ Entorno virtual activado: emr_ev"
else
    echo "❌ No se encontró entorno virtual emr_ev"
    echo "   Ejecutando: python3 -m venv emr_ev"
    python3 -m venv emr_ev
    source emr_ev/bin/activate
    echo "✅ Nuevo entorno virtual creado y activado"
    
    echo "📦 Instalando dependencias..."
    pip install -r requirements.txt
    pip install djangorestframework django-cors-headers
fi

# Verificar migraciones
echo "🔄 Verificando migraciones..."
python manage.py migrate

# Iniciar servidor Django (Backend)
echo "🐘 Iniciando servidor Django (Backend) en puerto 8000..."
python manage.py runserver 8000 > django.log 2>&1 &
DJANGO_PID=$!
echo "✅ Servidor Django iniciado (PID: $DJANGO_PID)"

# Esperar un momento para que Django se inicie
sleep 5

# Verificar si Django está funcionando
if curl -s http://localhost:8000/admin/ > /dev/null 2>&1; then
    echo "✅ Django está funcionando correctamente"
else
    echo "⚠️  Django puede estar tardando en iniciar..."
    echo "   Revisa el log: tail -f django.log"
fi

# Navegar al directorio frontend
echo "📁 Navegando al directorio frontend..."
cd frontend

# Verificar si node_modules existe
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias de React..."
    npm install
fi

# Iniciar servidor React (Frontend)
echo "⚛️  Iniciando servidor React (Frontend) en puerto 3000..."
npm start > react.log 2>&1 &
REACT_PID=$!
echo "✅ Servidor React iniciado (PID: $REACT_PID)"

# Volver al directorio raíz
cd ..

# Esperar un momento para que React se inicie
sleep 5

# Verificar si React está funcionando
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ React está funcionando correctamente"
else
    echo "⚠️  React puede estar tardando en iniciar..."
    echo "   Revisa el log: tail -f frontend/react.log"
fi

# Mostrar resumen
echo ""
echo "🎉 Servidores iniciados exitosamente!"
echo "======================================"
echo "🐘 Django (Backend): http://localhost:8000"
echo "   - Admin: http://localhost:8000/admin/"
echo "   - API: http://localhost:8000/api/"
echo ""
echo "⚛️  React (Frontend): http://localhost:3000"
echo ""
echo "📊 Logs:"
echo "   - Django: django.log"
echo "   - React: frontend/react.log"
echo ""
echo "🛑 Para detener todos los servidores:"
echo "   pkill -f 'manage.py runserver'"
echo "   pkill -f 'react-scripts start'"
echo ""
echo "🔍 Para verificar procesos:"
echo "   ps aux | grep -E '(runserver|react-scripts)'"
echo ""

# Función para limpiar al salir
cleanup() {
    echo ""
    echo "🛑 Deteniendo servidores..."
    kill $DJANGO_PID 2>/dev/null || true
    kill $REACT_PID 2>/dev/null || true
    pkill -f 'manage.py runserver' 2>/dev/null || true
    pkill -f 'react-scripts start' 2>/dev/null || true
    echo "✅ Servidores detenidos"
    exit 0
}

# Capturar señales para limpiar
trap cleanup SIGINT SIGTERM

# Mantener el script ejecutándose
echo "🔄 Los servidores están ejecutándose. Presiona Ctrl+C para detener..."
wait
