# Prompt maestro para Cursor — Actualización del EMR usando formularios físicos

Quiero que uses esta carpeta como **fuente funcional de referencia** para actualizar/mejorar el EMR existente.

Archivos obligatorios a leer:
- `README.md`
- `FORMULARIOS_TRANSCRIPCION.md`
- `MODELO_DATOS_REFERENCIA.json`
- `RECOMENDACIONES_EMR.md`
- todas las imágenes de `imagenes/`

## Objetivo

Comparar el EMR actual con los formularios físicos de internación del Instituto de Cardiología Pueblo de Luis y llevar al sistema digital toda la información clínicamente relevante que hoy se registra en papel, **sin destruir ni degradar funcionalidad existente**.

## Regla principal

**NO MODIFIQUES CÓDIGO TODAVÍA.**

Primero inspeccioná el proyecto completo:
- stack y versiones;
- modelos/entidades;
- migraciones y esquema de base de datos;
- APIs;
- formularios y componentes de UI;
- autenticación y roles;
- módulos actuales de historia clínica/internación;
- laboratorio;
- auditoría y firma si existen.

## Primera entrega obligatoria: GAP ANALYSIS

Generá un documento `docs/emr_gap_analysis_formularios.md` con una tabla que contenga:

| Formulario | Requisito/campo | Existe | Implementación actual | Problema | Cambio propuesto | Prioridad | Riesgo |
|---|---|---|---|---|---|---|---|

Clasificá `Existe` como:
- COMPLETO
- PARCIAL
- NO EXISTE
- EXISTE PERO DEBE REFACTORIZARSE

Incluí también un mapa:
`campo del formulario -> modelo -> tabla -> columna/API -> pantalla`

## Después del GAP ANALYSIS

Presentame un plan por fases. No hagas una migración gigante.

Para cada fase indicá:
1. archivos a modificar;
2. migraciones necesarias;
3. endpoints;
4. componentes/pantallas;
5. permisos;
6. tests;
7. criterios de aceptación;
8. mecanismo de rollback.

Esperá aprobación antes de implementar cambios destructivos o de arquitectura.

## Reglas de dominio obligatorias

### Internación
Los datos longitudinales deben pertenecer a un episodio/internación, no únicamente al paciente.

### Evoluciones y notas
Cada registro debe tener:
- paciente;
- internación/encounter;
- fecha/hora clínica;
- autor;
- rol;
- texto;
- estado;
- fecha de creación;
- auditoría.

No sobrescribir notas clínicas firmadas.

### Indicaciones
Separar:
- orden médica;
- programación;
- administración/cumplimiento.

No representar el cumplimiento únicamente con columnas horarias.

### Controles
Temperatura, pulso, presión arterial, frecuencia respiratoria y glucemia deben ser observaciones de serie temporal.

### Balance hídrico
Registrar cada ingreso/egreso individual y calcular automáticamente:
- total por hora;
- total por turno;
- total diario;
- balance neto.

### Laboratorio
No crear una tabla ancha con una columna por analito.
Usar un catálogo de analitos + resultados.
Preparar el diseño para integración posterior con LIMS/equipos.

### Compatibilidad
Reutilizá entidades y servicios existentes siempre que sean correctos.
No dupliques conceptos que ya existen.

## Calidad

Antes de cerrar cada fase:
- ejecutar tests existentes;
- agregar tests para lo nuevo;
- verificar migraciones up/down;
- revisar permisos;
- evitar pérdida de datos;
- documentar decisiones.

## Resultado esperado

El EMR debe cubrir funcionalmente estos módulos:
1. ingreso/anamnesis;
2. antecedentes;
3. examen inicial;
4. evolución médica;
5. kinesiología;
6. indicaciones médicas;
7. controles de enfermería;
8. cumplimiento de indicaciones/administración;
9. balance de terapia intensiva;
10. comentarios de enfermería;
11. laboratorio.

La interfaz digital puede mejorar el diseño del papel. Los formularios son la referencia de contenido, no una obligación de replicar visualmente cada grilla.
