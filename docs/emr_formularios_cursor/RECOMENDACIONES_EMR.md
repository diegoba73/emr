# Recomendaciones para actualizar el EMR a partir de los formularios

## 1. No copiar el papel 1:1

El papel mezcla identificación, órdenes, registros longitudinales y resultados. En un EMR conviene separar entidades y conservar relaciones.

## 2. Entidades clínicas recomendadas

- `Patient`
- `Encounter` / `Admission`
- `Allergy`
- `MedicationStatement` — medicación habitual
- `Problem` / antecedentes
- `FamilyHistory`
- `InitialAssessment`
- `PhysicalExam`
- `Diagnosis`
- `CarePlan`
- `ClinicalNote`
- `PhysiotherapyNote`
- `MedicationOrder`
- `MedicationAdministration`
- `VitalSign`
- `GlucoseMeasurement`
- `NursingNote`
- `FluidBalanceEntry`
- `LabOrder`
- `LabResult`

Los nombres reales deben adaptarse a la arquitectura existente del proyecto.

## 3. Reglas de modelado

### Registros repetibles
Evolución, kinesiología, enfermería y controles deben ser filas/eventos, nunca columnas adicionales por día.

### Fecha y hora
Todo evento clínico debe guardar al menos:
- `recorded_at`
- `performed_at` cuando aplique
- usuario/profesional autor
- rol
- sede/servicio
- estado
- auditoría de modificaciones

### Indicaciones vs. cumplimiento
Separar:
- **prescripción/orden**: qué se indicó;
- **programación**: cuándo debería ejecutarse;
- **administración/cumplimiento**: qué ocurrió realmente.

### Signos vitales
Modelarlos como observaciones con:
- tipo
- valor
- unidad
- fecha/hora
- origen
- profesional

### Balance hídrico
No almacenar únicamente totales. Registrar movimientos individuales:
- tipo: ingreso / egreso
- vía o categoría
- volumen
- unidad
- fecha/hora
- turno
- observación

Los totales se calculan.

### Laboratorio
Usar catálogo de analitos. Cada resultado debería poder guardar:
- analito
- resultado
- unidad
- rango de referencia
- flag
- método/equipo si existe
- muestra
- fecha/hora de toma
- fecha/hora de validación
- profesional
- estado

Evitar una tabla con columnas `hemoglobina`, `urea`, `creatinina`, etc. para esta planilla.

## 4. Campos del papel que requieren normalización

- `RIN`: revisar si es la denominación histórica de `INR`.
- `CO3H`: revisar si corresponde a `HCO3−`.
- `GOT`: puede mostrarse como GOT/AST según nomenclatura institucional.
- `EAOP`, `IC`, `IRC`, `EPOC`: conservar etiqueta institucional y agregar descripción expandida en interfaz o catálogo.
- `Angor-IAM`: conviene separar dos antecedentes si clínicamente el sistema ya los diferencia.

No modificar estas denominaciones automáticamente sin revisar el modelo actual.

## 5. Requisitos médico-legales y de seguridad

- No borrar ni sobrescribir una evolución validada.
- Correcciones mediante nueva versión/adenda y auditoría.
- Firma/validación con usuario autenticado.
- Control de acceso por rol.
- Registro de creación, modificación y validación.
- Evitar que personal sin permisos edite indicaciones firmadas.
- Mantener vínculo con internación/episodio.
- Registrar habitación/cama históricamente, no solo el valor actual.

## 6. Estrategia de implementación

1. Inventariar el EMR actual.
2. Mapear campos existentes vs. formularios.
3. Clasificar cada requisito:
   - ya existe;
   - existe parcialmente;
   - falta;
   - existe pero con modelo inadecuado.
4. Proponer cambios mínimos y compatibles.
5. Crear migraciones reversibles.
6. Implementar backend.
7. Implementar UI.
8. Agregar tests.
9. Verificar criterios de aceptación.
10. Recién entonces pasar al siguiente módulo.

## 7. Orden sugerido

1. Internación / anamnesis.
2. Antecedentes + examen de ingreso.
3. Evoluciones.
4. Indicaciones médicas.
5. Cumplimiento / administración.
6. Controles de enfermería.
7. Comentarios de enfermería.
8. Kinesiología.
9. Balance hídrico.
10. Laboratorio / integración con LIMS.
