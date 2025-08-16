#!/bin/bash

echo "🧹 LIMPIANDO Y REINICIANDO TODO EL SISTEMA EMR..."
echo "=================================================="

# Matar TODOS los procesos relacionados
echo "🔪 Matando todos los procesos..."

# Matar procesos de Django
pkill -f 'manage.py runserver' 2>/dev/null || true
pkill -f 'python.*runserver' 2>/dev/null || true

# Matar procesos de React
pkill -f 'react-scripts start' 2>/dev/null || true
pkill -f 'npm start' 2>/dev/null || true
pkill -f 'node.*react-scripts' 2>/dev/null || true

# Matar procesos en puertos específicos
echo "🔌 Liberando puertos..."

# Puerto 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Matando proceso en puerto 8000..."
    lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
fi

# Puerto 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Matando proceso en puerto 3000..."
    lsof -Pi :3000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
fi

# Puerto 8001 (por si acaso)
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Matando proceso en puerto 8001..."
    lsof -Pi :8001 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
fi

# Puerto 3001 (por si acaso)
if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Matando proceso en puerto 3001..."
    lsof -Pi :3001 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
fi

echo "✅ Procesos terminados"
echo "⏳ Esperando 3 segundos..."
sleep 3

# Verificar que los puertos estén libres
echo "🔍 Verificando puertos..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Puerto 8000 aún ocupado"
    exit 1
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Puerto 3000 aún ocupado"
    exit 1
fi

echo "✅ Puertos 8000 y 3000 libres"

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
sleep 5

# Verificar que Django esté funcionando
echo "🔍 Verificando Django..."
if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
    echo "✅ Django funcionando correctamente"
else
    echo "❌ Error: Django no responde"
    exit 1
fi

# Iniciar React en background
echo "⚛️  Iniciando servidor React (Frontend) en puerto 3000..."
cd frontend
npm start > ../react.log 2>&1 &
REACT_PID=$!
cd ..
echo "✅ Servidor React iniciado (PID: $REACT_PID)"

# Esperar un poco para que React inicie
sleep 10

# Verificar que React esté funcionando
echo "🔍 Verificando React..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ React funcionando correctamente"
else
    echo "❌ Error: React no responde"
    exit 1
fi

echo ""
echo "🎉 SISTEMA REINICIADO EXITOSAMENTE!"
echo "==================================="
echo "🐘 Django (Backend): http://localhost:8000"
echo "   - Admin: http://localhost:8000/admin/"
echo "   - API: http://localhost:8000/api/"
echo "⚛️  React (Frontend): http://localhost:3000"
echo ""
echo "📊 Logs:"
echo "   - Django: django.log"
echo "   - React: react.log"
echo ""
echo "🔐 Credenciales de prueba:"
echo "   - Secretaria: secretaria1 / changeme123"
echo "   - Paciente: paciente1 / changeme123"
echo "   - Médico: medico1 / changeme123"
echo ""
echo "🛑 Para detener: pkill -f 'manage.py runserver' && pkill -f 'react-scripts start'"
echo ""
echo "🔄 Los servidores están ejecutándose. Presiona Ctrl+C para detener..."

# Mantener el script corriendo
wait
