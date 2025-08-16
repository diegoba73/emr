# 🏥 Implementación de Centros Físicos y Tipos de Atención

## 📋 Resumen de la Implementación

Se ha implementado un sistema completo para manejar los dos centros físicos de la clínica (CEHTA e ICPL) y los diferentes tipos de atención médica, incluyendo internaciones.

## 🏢 Centros Físicos Implementados

### 1. **CEHTA** - Centro de Atención Ambulatoria
- **Ubicación**: Centro especializado en atención ambulatoria
- **Servicios**: Consultas médicas ambulatorias sin internación
- **Tipo de Atención**: Ambulatoria

### 2. **ICPL** - Instituto Cardiológico con Internación
- **Ubicación**: Instituto cardiológico con capacidad completa
- **Servicios**: 
  - Guardia cardiológica
  - Internación UCO (Terapia Intensiva)
  - Internación UCE (Observación/Intermedia)
  - Cirugía ambulatoria
  - Cirugía compleja con internación

## 🏥 Tipos de Atención Implementados

### Para CEHTA:
- **AMBULATORIA**: Consultas médicas ambulatorias sin internación

### Para ICPL:
- **GUARDIA_CARDIOLOGICA**: Atención de urgencias cardiológicas
- **INTERNACION_UCO**: Internación en Unidad de Cuidados Intensivos
- **INTERNACION_UCE**: Internación en Unidad de Cuidados Especiales
- **CIRUGIA_AMBULATORIA**: Intervenciones quirúrgicas sin internación
- **CIRUGIA_COMPLEJA**: Intervenciones quirúrgicas complejas con internación

## 🛏️ Áreas de Internación Implementadas

### En ICPL:
1. **UCO** - Unidad de Cuidados Intensivos (8 camas)
2. **UCE** - Unidad de Cuidados Especiales (12 camas)
3. **PISO_GENERAL** - Piso general para pacientes estables (20 camas)
4. **CIRUGIA** - Área especializada para pacientes post-quirúrgicos (6 camas)

## 📊 Modelos de Base de Datos Creados

### 1. **CentroFisico**
- Código único (CEHTA, ICPL)
- Nombre y descripción
- Dirección y teléfono
- Estado activo/inactivo

### 2. **TipoAtencion**
- Código único del tipo
- Nombre y descripción
- Centro físico asociado
- Requiere internación (sí/no)
- Es urgencia (sí/no)

### 3. **AreaInternacion**
- Código único del área
- Nombre y descripción
- Centro físico asociado
- Capacidad de camas

### 4. **CamaInternacion**
- Número de cama
- Área asociada
- Estado (Disponible, Ocupada, Mantenimiento, Reservada)
- Tipo de cama (Estándar, UCI, UCE, Post-quirúrgica)

### 5. **Internacion**
- Paciente internado
- Médico responsable
- Cama asignada
- Turno de origen (opcional)
- Fechas de ingreso y alta
- Motivo de ingreso y diagnóstico
- Estado de la internación
- Número de internación automático

## 🔧 Modificaciones Realizadas

### 1. **Modelo Turno**
- Agregados campos `centro_fisico` y `tipo_atencion`
- Campos opcionales para compatibilidad con datos existentes

### 2. **APIs Implementadas**
- `/api/catalogos/centros-fisicos/` - Gestión de centros físicos
- `/api/catalogos/tipos-atencion/` - Gestión de tipos de atención
- `/api/catalogos/areas-internacion/` - Gestión de áreas de internación
- `/api/catalogos/camas-internacion/` - Gestión de camas
- `/api/internaciones/` - Gestión de internaciones

### 3. **Funcionalidades de Internación**
- Crear nueva internación
- Dar alta médica
- Estadísticas por estado y centro
- Filtros por centro, área y estado
- Control automático de disponibilidad de camas

## 🎯 Flujo de Trabajo Implementado

### 1. **Atención Ambulatoria (CEHTA)**
```
Paciente → Turno (CEHTA, Ambulatoria) → Consulta → Alta
```

### 2. **Guardia Cardiológica (ICPL)**
```
Paciente → Turno (ICPL, Guardia) → Evaluación → Alta o Internación
```

### 3. **Internación (ICPL)**
```
Paciente → Turno (ICPL, Internación) → Internación → Seguimiento → Alta
```

### 4. **Cirugía (ICPL)**
```
Paciente → Turno (ICPL, Cirugía) → Intervención → Internación → Alta
```

## 🔐 Control de Acceso

### **Médicos**
- Ven sus propias internaciones
- Pueden crear internaciones
- Pueden dar altas médicas

### **Administradores**
- Ven todas las internaciones
- Gestión completa del sistema

### **Otros Roles**
- No tienen acceso a internaciones

## 📈 Estadísticas Disponibles

### **Por Estado**
- Activas
- Altas médicas
- Altas voluntarias

### **Por Centro**
- CEHTA
- ICPL

### **Por Área**
- UCO
- UCE
- Piso General
- Cirugía

## 🚀 Próximos Pasos Sugeridos

1. **Frontend**: Crear interfaces para gestión de internaciones
2. **Reportes**: Generar reportes de ocupación y estadísticas
3. **Notificaciones**: Sistema de alertas para camas disponibles
4. **Integración**: Conectar con sistema de facturación
5. **Móvil**: App para médicos en guardia

## ✅ Estado Actual

- ✅ Modelos de base de datos implementados
- ✅ APIs REST completas
- ✅ Control de acceso por roles
- ✅ Datos iniciales poblados
- ✅ Migraciones aplicadas
- ✅ Serializers y ViewSets configurados

**El sistema está listo para ser utilizado en producción.**


