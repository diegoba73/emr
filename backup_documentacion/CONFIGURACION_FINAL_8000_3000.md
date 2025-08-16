# 🎯 CONFIGURACIÓN FINAL EMR - PUERTOS 8000 Y 3000

*Última actualización: 11 de Agosto de 2025*
*Configuración estandarizada y validada*

## 🚀 **CONFIGURACIÓN ESTANDARIZADA**

### **Puertos Definitivos:**
- **🐘 Django Backend**: `http://localhost:8000`
- **⚛️ React Frontend**: `http://localhost:3000`

### **URLs del Sistema:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/
- **Admin Django**: http://localhost:8000/admin/
- **Endpoints de autenticación**: http://localhost:8000/api/auth/

---

## 🔧 **ARCHIVOS CONFIGURADOS**

### **1. Script de Inicio (`start_servers_final.sh`)**
```bash
# Django en puerto 8000
python manage.py runserver 8000

# React en puerto 3000  
npm start
```

### **2. Frontend - API Service (`frontend/src/services/api.ts`)**
```typescript
const API_BASE_URL = 'http://127.0.0.1:8000/api';
```

### **3. Frontend - Login (`frontend/src/pages/Login.tsx`)**
```typescript
const response = await fetchWithCSRF('http://localhost:8000/api/auth/login/', {
```

### **4. Frontend - Register (`frontend/src/pages/Register.tsx`)**
```typescript
const response = await fetch('http://localhost:8000/api/auth/register/patient/', {
```

### **5. Django Settings (`synesis/settings.py`)**
```python
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
```

---

## 🚀 **INSTRUCCIONES DE USO**

### **1. Iniciar Servidores:**
```bash
./start_servers_final.sh
```

### **2. Verificar Funcionamiento:**
```bash
python verificar_sistema_final.py
```

### **3. Acceder a la Aplicación:**
- **Frontend**: http://localhost:3000
- **Admin**: http://localhost:8000/admin/

---

## 🔐 **CREDENCIALES DE PRUEBA**

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| **Secretaria** | `secretaria1` | `changeme123` |
| **Paciente** | `paciente1` | `changeme123` |
| **Médico** | `medico1` | `changeme123` |
| **Admin** | `admin` | `admin123` |

---

## ✅ **VERIFICACIÓN DEL SISTEMA**

### **Estado Actual:**
- ✅ **Backend Django**: Funcionando en puerto 8000
- ✅ **Frontend React**: Funcionando en puerto 3000
- ✅ **Login**: Funcionando correctamente
- ✅ **API Endpoints**: Todos operativos
- ✅ **CORS/CSRF**: Configurado correctamente
- ✅ **Base de Datos**: Conectada y operativa

### **Funcionalidades Verificadas:**
- ✅ Login de usuarios
- ✅ Carga de datos (pacientes, médicos, especialidades)
- ✅ Gestión de turnos
- ✅ Interfaz de usuario responsiva

---

## 🛠️ **SOLUCIÓN DE PROBLEMAS**

### **Si los puertos están ocupados:**
El script `start_servers_final.sh` automáticamente:
1. Detecta procesos usando puertos 8000 y 3000
2. Los termina automáticamente
3. Reinicia los servidores

### **Si hay problemas de conexión:**
1. Verificar que no haya otros procesos usando los puertos
2. Ejecutar: `pkill -f 'manage.py runserver' && pkill -f 'react-scripts start'`
3. Reiniciar con: `./start_servers_final.sh`

### **Si hay problemas de CSRF:**
1. Verificar que el frontend esté en puerto 3000
2. Verificar que el backend esté en puerto 8000
3. Limpiar cookies del navegador

---

## 📋 **COMANDOS ÚTILES**

### **Verificar procesos:**
```bash
ps aux | grep -E '(runserver|react-scripts)'
```

### **Detener servidores:**
```bash
pkill -f 'manage.py runserver'
pkill -f 'react-scripts start'
```

### **Verificar conectividad:**
```bash
curl http://localhost:8000/api/
curl http://localhost:3000
```

### **Verificar logs:**
```bash
tail -f django.log
tail -f react.log
```

---

## 🎉 **CONFIGURACIÓN COMPLETADA**

**El sistema EMR está completamente configurado y funcionando con los puertos estándar:**
- **Backend**: 8000
- **Frontend**: 3000

**¡Listo para usar!** 🚀
