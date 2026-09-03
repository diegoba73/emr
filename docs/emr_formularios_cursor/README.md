# Formularios de Historia Clínica — material de referencia para Cursor

## Objetivo

Este paquete transcribe y estructura los formularios en papel actualmente utilizados por el Instituto de Cardiología Pueblo de Luis para que Cursor pueda compararlos con el EMR existente y proponer/mejorar la implementación digital.

**Importante:** los formularios fotografiados están en blanco. El objetivo es modelar su estructura, no extraer información de un paciente.

## Archivos

- `CURSOR_PROMPT.md`: prompt recomendado para ejecutar dentro del repositorio del EMR.
- `FORMULARIOS_TRANSCRIPCION.md`: transcripción funcional de los 10 formularios.
- `MODELO_DATOS_REFERENCIA.json`: representación estructurada y tipada de campos/secciones.
- `RECOMENDACIONES_EMR.md`: criterios de diseño para digitalizar sin copiar literalmente las limitaciones del papel.
- `imagenes/`: los 10 formularios convertidos a PNG y renombrados de forma semántica.

## Estrategia recomendada

1. Copiar esta carpeta dentro del repositorio del EMR, por ejemplo en `docs/formularios_historia_clinica/`.
2. Abrir Cursor en la raíz del proyecto.
3. Pedirle que lea primero `CURSOR_PROMPT.md`.
4. Hacer que inspeccione el código y la base de datos actuales.
5. Exigir un **gap analysis** antes de modificar código.
6. Implementar por módulos, con migraciones reversibles, tests y criterios de aceptación.

## Principio clave

Los formularios sirven como **fuente funcional**. No conviene reproducir el papel 1:1 en pantalla. En particular:
- evoluciones, comentarios, kinesiología y administraciones deben modelarse como registros repetibles con fecha/hora/autor;
- resultados de laboratorio deben ser observaciones por analito, no columnas fijas;
- indicaciones médicas y cumplimiento/administración deben ser entidades diferentes;
- controles de enfermería deben ser series temporales;
- todo dato clínico debe conservar autoría, fecha/hora y trazabilidad.
