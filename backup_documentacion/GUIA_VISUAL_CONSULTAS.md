# 🎯 Guía Visual: Cómo Encontrar y Usar "Crear Consulta"

## 📍 **Paso 1: Acceder al Sistema**

1. **Abre tu navegador** y ve a: `http://localhost:3000`
2. **Inicia sesión como médico** con cualquiera de estas credenciales:
   - Usuario: `dr.garcia` / Contraseña: `medico123`
   - Usuario: `dra.rodriguez` / Contraseña: `medico123`
   - Usuario: `dr.lopez` / Contraseña: `medico123`
   - Usuario: `dra.martinez` / Contraseña: `medico123`
   - Usuario: `dr.gonzalez` / Contraseña: `medico123`

## 📍 **Paso 2: Navegar a "Mis Turnos"**

Una vez logueado, verás el menú lateral izquierdo:

```
┌─────────────────────────────────────┐
│ 🏠 Dashboard                        │
│ 📅 Mis Turnos  ← HAZ CLIC AQUÍ     │ ← ESTE ES EL ENLACE
│ 📋 Mis Consultas                    │
└─────────────────────────────────────┘
```

**Haz clic en "📅 Mis Turnos"**

## 📍 **Paso 3: Ver la Página de Mis Turnos**

Verás una página que se ve así:

```
┌─────────────────────────────────────┐
│ 👨‍⚕️ Mis Turnos                    │
├─────────────────────────────────────┤
│ 📊 Estadísticas:                    │
│ ┌─────────┬─────────┬─────────────┐ │
│ │ 2       │ 1       │ 3           │ │
│ │Pendientes│Confirmados│Realizados │ │
│ └─────────┴─────────┴─────────────┘ │
├─────────────────────────────────────┤
│ Filtro: [Todos los estados ▼]   │
└─────────────────────────────────────┘
```

## 📍 **Paso 4: Buscar Turnos Reservados**

En la lista de turnos, busca uno que tenga el estado **"RESERVADO"**:

```
┌─────────────────────────────────────┐
│ 14:30    │ [RESERVADO]              │ ← BUSCA ESTE ESTADO
│ Mar 15   │                          │
├─────────────────────────────────────┤
│ 👤 Paciente: Juan Pérez             │
│ 🏥 Especialidad: Cardiología        │
│ 📝 Motivo: Dolor en el pecho        │
├─────────────────────────────────────┤
│ [✅ Confirmar]                      │ ← PRIMERO HAZ CLIC AQUÍ
└─────────────────────────────────────┘
```

**Haz clic en "✅ Confirmar"**

## 📍 **Paso 5: Confirmar el Turno**

Aparecerá un mensaje de confirmación. Haz clic en "Aceptar".

El turno cambiará a estado **"CONFIRMADO"**:

```
┌─────────────────────────────────────┐
│ 14:30    │ [CONFIRMADO]             │ ← ESTADO CAMBIADO
│ Mar 15   │                          │
├─────────────────────────────────────┤
│ 👤 Paciente: Juan Pérez             │
│ 🏥 Especialidad: Cardiología        │
│ 📝 Motivo: Dolor en el pecho        │
├─────────────────────────────────────┤
│ [📋 Crear Consulta]                 │ ← AHORA APARECE ESTE BOTÓN
└─────────────────────────────────────┘
```

## 📍 **Paso 6: Crear la Consulta**

**Haz clic en "📋 Crear Consulta"**

Se abrirá un modal grande que se ve así:

```
┌─────────────────────────────────────────────────────────┐
│ 📋 Nueva Consulta                    [✕]                │
├─────────────────────────────────────────────────────────┤
│ 📋 Información del Turno:                               │
│ Paciente: Juan Pérez                                    │
│ Fecha: 15/03/2024                                       │
│ Hora: 14:30                                             │
│ Motivo: Dolor en el pecho                               │
├─────────────────────────────────────────────────────────┤
│ 📝 Anamnesis (Interrogatorio)                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [ESCRIBE AQUÍ el interrogatorio]                   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 🔍 Examen Físico                                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [ESCRIBE AQUÍ los hallazgos del examen]            │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 🏥 Diagnóstico Presuntivo                               │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [ESCRIBE AQUÍ el diagnóstico]                      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 💊 Plan de Manejo / Conducta                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [ESCRIBE AQUÍ el tratamiento]                      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 📋 Notas Médicas Adicionales                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [ESCRIBE AQUÍ observaciones adicionales]           │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    [Cancelar] [Guardar Consulta]       │
└─────────────────────────────────────────────────────────┘
```

## 📍 **Paso 7: Completar el Formulario**

Llena todos los campos:

1. **📝 Anamnesis**: Describe el interrogatorio
2. **🔍 Examen Físico**: Describe los hallazgos
3. **🏥 Diagnóstico Presuntivo**: Escribe el diagnóstico
4. **💊 Plan de Manejo**: Describe el tratamiento
5. **📋 Notas Médicas**: Observaciones adicionales

## 📍 **Paso 8: Guardar la Consulta**

**Haz clic en "Guardar Consulta"**

El modal se cerrará y verás que el turno cambió a estado **"REALIZADO"**:

```
┌─────────────────────────────────────┐
│ 14:30    │ [REALIZADO]              │ ← ESTADO FINAL
│ Mar 15   │                          │
├─────────────────────────────────────┤
│ 👤 Paciente: Juan Pérez             │
│ 🏥 Especialidad: Cardiología        │
│ 📝 Motivo: Dolor en el pecho        │
├─────────────────────────────────────┤
│ [✅ Realizado]                      │ ← SIN ACCIONES (completado)
└─────────────────────────────────────┘
```

## 🎯 **Resumen del Flujo**

```
RESERVADO → [✅ Confirmar] → CONFIRMADO → [📋 Crear Consulta] → REALIZADO
```

## ❓ **¿No ves el botón "Crear Consulta"?**

### Posibles causas:

1. **No estás logueado como médico**
   - Verifica que tu usuario tenga rol "MEDICO"

2. **No hay turnos confirmados**
   - Primero debes confirmar un turno reservado

3. **El turno ya tiene consulta**
   - Si el turno está en estado "REALIZADO", ya tiene consulta

4. **Problema de permisos**
   - Solo los médicos pueden crear consultas

### Para verificar tu rol:

En el menú lateral, verás tu información de usuario:

```
┌─────────────────────────────────────┐
│ 👨‍⚕️ Dr. Carlos Rodríguez           │ ← DEBE DECIR "Médico"
│ Médico                              │
│ 🚪 Cerrar Sesión                    │
└─────────────────────────────────────┘
```

## 🔧 **Solución de Problemas**

Si no ves la funcionalidad:

1. **Reinicia el navegador**
2. **Limpia la caché** (Ctrl+F5 o Cmd+Shift+R)
3. **Verifica que los servidores estén corriendo**:
   - Backend: `http://localhost:8000`
   - Frontend: `http://localhost:3000`
4. **Verifica las credenciales** del médico

## 📞 **¿Necesitas Ayuda?**

Si sigues sin ver la funcionalidad, ejecuta este comando para verificar que todo esté funcionando:

```bash
python test_consultas_simple.py
```

Esto te dirá si las APIs están disponibles y funcionando correctamente.
