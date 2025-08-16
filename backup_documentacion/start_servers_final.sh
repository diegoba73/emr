#!/bin/bash

echo "🚀 Iniciando servidores del proyecto EMR..."
echo "=========================================="

# Verificar si los puertos están disponibles
echo "🔍 Verificando puertos..."

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Puerto 8000 en uso. Deteniendo proceso..."
    pkill -f 'manage.py runserver'
    sleep 2
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Puerto 3000 en uso. Deteniendo proceso..."
    pkill -f 'react-scripts start'
    sleep 2
fi

echo "✅ Puertos disponibles"

# Activar entorno virtual
echo "🐍 Activando entorno virtual..."
source emr_ev/bin/activate
echo "✅ Entorno virtual activado: emr_ev"

# Verificar migraciones
echo "🔄 Verificando migraciones..."
python manage.py migrate

# Iniciar Django en background
echo "🐘 Iniciando servidor Django (Backend) en puerto 8000..."
python manage.py runserver 8000 > django.log 2>&1 &
DJANGO_PID=$!
echo "✅ Servidor Django iniciado (PID: $DJANGO_PID)"

# Esperar un poco para que Django inicie
sleep 3

# Iniciar React en background
echo "⚛️  Iniciando servidor React (Frontend) en puerto 3000..."
cd frontend
npm start > ../react.log 2>&1 &
REACT_PID=$!
cd ..
echo "✅ Servidor React iniciado (PID: $REACT_PID)"

# Esperar un poco para que React inicie
sleep 5

echo ""
echo "🎉 Servidores iniciados exitosamente!"
echo "======================================"
echo "🐘 Django (Backend): http://localhost:8000"
echo "   - Admin: http://localhost:8000/admin/"
echo "   - API: http://localhost:8000/api/"
echo "⚛️  React (Frontend): http://localhost:3000"
echo ""
echo "📊 Logs:"
echo "   - Django: django.log"
echo "   - React: react.log"
echo ""
echo "🛑 Para detener todos los servidores:"
echo "   pkill -f 'manage.py runserver'"
echo "   pkill -f 'react-scripts start'"
echo ""
echo "🔍 Para verificar procesos:"
echo "   ps aux | grep -E '(runserver|react-scripts)'"
echo ""
echo "🔄 Los servidores están ejecutándose. Presiona Ctrl+C para detener..."

# Mantener el script corriendo
wait
