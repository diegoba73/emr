# Importación de Catalogo_reactivos.csv — 2026-09-23

Aplicada al EMR local (emr_backend / synesis_db).

- 56 filas agrupadas en 53 productos.
- 35 productos creados sin stock; 16 actualizados; 2 sin cambios.
- Se conservaron SKU, equipos, proveedores y vínculos de consumo existentes.
- Cuatro REF corregidas según CSV: HDL 1009804 → 1008102; Proti U/LCR 1008161 → 1690007; Mg-color 1008145 → 1580001; UIBC/TIBC 1008123 → 1492361.
- Referencias dudosas de fotos 6, 11, 19, 29 y 31 pendientes: permanecen vacías en las altas.
- Sin crear lotes ni modificar cantidades, movimientos o consumos. Los productos nuevos usan unidad kit; debe revisarse antes de ingresar existencias.
- Controles, calibradores y limpieza se dieron de alta como insumos OTRO, sin configurar QC. No se asignaron equipos a las altas.
- Conservación, contenido, fabricante, estado de revisión, lotes y fechas originales quedan conservados por fila en el informe JSON; no se incorporaron como campos estructurados del EMR.
- Verificado: cinco pruebas aprobadas; repetir la planificación produce 53 productos sin cambios.

Detalle y valores anteriores: archivos locales `import-reactivos-aplicado-20260923.json`
y `import-reactivos-respaldo-20260923.json` (no versionados).
Para producción: [procedimiento de actualización](despliegue-20260924.md).
