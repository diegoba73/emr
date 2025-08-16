# 🎉 Servidores EMR Activos

## ✅ Estado Actual

**Todos los servidores están funcionando correctamente:**

- 🐘 **Django (Backend)**: ✅ Activo en puerto 8000
- ⚛️ **React (Frontend)**: ✅ Activo en puerto 3000

## 🌐 URLs de Acceso

| Servicio | URL | Estado |
|----------|-----|--------|
| **Frontend (React)** | http://localhost:3000 | ✅ Activo |
| **Backend (Django)** | http://localhost:8000 | ✅ Activo |
| **Admin Django** | http://localhost:8000/admin/ | ✅ Activo |
| **API Django** | http://localhost:8000/api/ | ✅ Activo |

## 🔐 Credenciales de Acceso

### Superusuario Admin (Recién Creado)
- **Usuario**: `admin2`
- **Email**: `diegobaulde@gmail.com`
- **Contraseña**: (La que ingresaste al crear el superusuario)
- **URL**: http://localhost:8000/admin/

### Usuarios de Médicos (Datos de Prueba)
- **Usuario**: `dr.garcia`
- **Contraseña**: `changeme123`
- **Rol**: Médico

- **Usuario**: `dra.rodriguez`
- **Contraseña**: `changeme123`
- **Rol**: Médico

- **Usuario**: `dr.lopez`
- **Contraseña**: `changeme123`
- **Rol**: Médico

## 🛠️ Comandos Útiles

### Verificar Servidores
```bash
# Verificar procesos activos
ps aux | grep -E "(runserver|react-scripts)" | grep -v grep

# Verificar puertos
lsof -i :8000
lsof -i :3000
```

### Detener Servidores
```bash
# Detener todos los servidores
pkill -f "manage.py runserver"
pkill -f "react-scripts start"

# O por puerto específico
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### Reiniciar Servidores
```bash
# Usar el script automático
./start_servers_fixed.sh

# O manualmente
# Terminal 1: Django
cd /Users/diegobaulde/Downloads/emr
source emr_ev/bin/activate
python manage.py runserver 8000

# Terminal 2: React
cd /Users/diegobaulde/Downloads/emr/frontend
npm start
```

## 📊 Logs

Los logs se guardan en:
- **Django**: `django.log` (directorio raíz)
- **React**: `frontend/react.log`

Para ver logs en tiempo real:
```bash
# Django
tail -f django.log

# React
tail -f frontend/react.log
```

## 🎯 Próximos Pasos

1. **Acceder al Admin**: http://localhost:8000/admin/
2. **Explorar el Frontend**: http://localhost:3000
3. **Probar la API**: http://localhost:8000/api/

## 🔧 Troubleshooting

### Si no puedes acceder al admin:
1. Verifica que Django esté corriendo: `ps aux | grep runserver`
2. Intenta acceder a: http://localhost:8000/admin/
3. Usa las credenciales del superusuario creado

### Si el frontend no carga:
1. Verifica que React esté corriendo: `ps aux | grep react-scripts`
2. Revisa los logs: `tail -f frontend/react.log`
3. Intenta acceder a: http://localhost:3000

### Si hay errores de base de datos:
```bash
python manage.py migrate
python manage.py check
```

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs mencionados arriba
2. Verifica que los puertos 8000 y 3000 estén libres
3. Asegúrate de que el entorno virtual esté activado
4. Ejecuta `python manage.py check` para verificar la configuración

---
**Fecha de creación**: $(date)
**Estado**: ✅ Todos los servidores activos y funcionando
