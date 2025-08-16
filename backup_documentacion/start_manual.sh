#!/bin/bash

# Script manual para iniciar servidores EMR
# Uso: ./start_manual.sh

echo "🚀 Iniciando servidores EMR manualmente..."

# 1. Activar entorno virtual
echo "🐍 Activando entorno virtual..."
if [ -d "emr_ev" ]; then
    source emr_ev/bin/activate
    echo "✅ Entorno: emr_ev"
elif [ -d "emr_env" ]; then
    source emr_env/bin/activate
    echo "✅ Entorno: emr_env"
else
    echo "❌ No se encontró entorno virtual"
    exit 1
fi

# 2. Verificar migraciones
echo "🔄 Verificando migraciones..."
python manage.py migrate

# 3. Iniciar Django (Terminal 1)
echo ""
echo "🐘 Para iniciar Django (Backend):"
echo "   python manage.py runserver 8000"
echo "   URL: http://localhost:8000"
echo "   Admin: http://localhost:8000/admin/"
echo ""

# 4. Iniciar React (Terminal 2)
echo "⚛️  Para iniciar React (Frontend):"
echo "   cd frontend"
echo "   npm start"
echo "   URL: http://localhost:3000"
echo ""

echo "📋 Comandos completos:"
echo "======================"
echo ""
echo "Terminal 1 (Django):"
echo "  cd /Users/diegobaulde/Downloads/emr"
echo "  source emr_ev/bin/activate"
echo "  python manage.py runserver 8000"
echo ""
echo "Terminal 2 (React):"
echo "  cd /Users/diegobaulde/Downloads/emr/frontend"
echo "  npm start"
echo ""
echo "🎯 URLs importantes:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend: http://localhost:8000"
echo "  - Admin: http://localhost:8000/admin/"
echo "  - API: http://localhost:8000/api/"
echo ""
