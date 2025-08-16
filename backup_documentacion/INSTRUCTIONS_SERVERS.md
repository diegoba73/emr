# 🚀 Instrucciones para Iniciar Servidores EMR

## 📋 Resumen Rápido

Tu proyecto EMR tiene dos componentes principales:
1. **Backend (Django)** - Puerto 8000
2. **Frontend (React)** - Puerto 3000

## 🎯 Métodos para Iniciar Servidores

### Método 1: Script Automático (Recomendado)

```bash
# Desde el directorio raíz del proyecto
./start_servers.sh
```

Este script:
- ✅ Activa el entorno virtual automáticamente
- ✅ Verifica y aplica migraciones
- ✅ Inicia Django en puerto 8000
- ✅ Inicia React en puerto 3000
- ✅ Muestra URLs y logs
- ✅ Limpia procesos al salir (Ctrl+C)

### Método 2: Script Manual

```bash
# Desde el directorio raíz del proyecto
./start_manual.sh
```

Este script te muestra los comandos exactos para ejecutar manualmente.

### Método 3: Manual (Paso a Paso)

#### Terminal 1 - Django (Backend)

```bash
# 1. Navegar al directorio del proyecto
cd /Users/diegobaulde/Downloads/emr

# 2. Activar entorno virtual
source emr_ev/bin/activate

# 3. Verificar migraciones
python manage.py migrate

# 4. Iniciar servidor Django
python manage.py runserver 8000
```

#### Terminal 2 - React (Frontend)

```bash
# 1. Navegar al directorio frontend
cd /Users/diegobaulde/Downloads/emr/frontend

# 2. Instalar dependencias (si es necesario)
npm install

# 3. Iniciar servidor React
npm start
```

## 🌐 URLs Importantes

Una vez iniciados los servidores:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost:3000 | Interfaz principal de React |
| **Backend** | http://localhost:8000 | API de Django |
| **Admin** | http://localhost:8000/admin/ | Panel de administración |
| **API** | http://localhost:8000/api/ | Endpoints de la API |

## 🔧 Verificación

### Verificar Django
```bash
curl http://localhost:8000/admin/
```

### Verificar React
```bash
curl http://localhost:3000
```

## 🛑 Detener Servidores

### Opción 1: Script Automático
```bash
# Presionar Ctrl+C en la terminal donde ejecutaste start_servers.sh
```

### Opción 2: Manual
```bash
# Detener todos los procesos de Django
pkill -f "manage.py runserver"

# Detener todos los procesos de React
pkill -f "react-scripts start"
```

### Opción 3: Por Puerto
```bash
# Detener proceso en puerto 8000 (Django)
lsof -ti:8000 | xargs kill -9

# Detener proceso en puerto 3000 (React)
lsof -ti:3000 | xargs kill -9
```

## 🔍 Troubleshooting

### Puerto ya en uso
```bash
# Verificar qué está usando el puerto
lsof -i :8000
lsof -i :3000

# Matar el proceso
kill -9 <PID>
```

### Errores de dependencias
```bash
# Reinstalar dependencias de Python
pip install -r requirements.txt

# Reinstalar dependencias de Node
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Errores de migración
```bash
python manage.py migrate --run-syncdb
```

## 📊 Logs

Los logs se guardan en:
- **Django**: `django.log` (directorio raíz)
- **React**: `frontend/react.log`

## 🎯 Datos de Prueba

Después de iniciar los servidores, puedes acceder con:

### Usuarios de Médicos (Admin)
- Usuario: `dr.garcia`
- Contraseña: `changeme123`
- URL: http://localhost:8000/admin/

### Crear Superusuario
```bash
python manage.py createsuperuser
```

## 📞 Soporte

Si encuentras problemas:
1. Verifica que los puertos 8000 y 3000 estén libres
2. Asegúrate de que el entorno virtual esté activado
3. Revisa los logs en los archivos mencionados
4. Ejecuta `python manage.py check` para verificar la configuración
