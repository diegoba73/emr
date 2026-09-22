# Ticket B — Dry-run catálogo reactivos (2026-09-21)

**Estado:** preparación + dry-run. **Carga real NO ejecutada** (falta autorización).

## 1. Archivos

| Archivo | Rol |
|---------|-----|
| `laboratorio/reactivos_matriz_catalogo.py` | Matriz confirmada + pendientes |
| `laboratorio/management/commands/cargar_reactivos_equipo_matriz.py` | Dry-run default; `--apply` no usado |
| `laboratorio/tests/test_cargar_reactivos_matriz.py` | Prueba dry-run sin escrituras |

## 2. Resultado dry-run (Docker/dev)

```
Propuestos confirmados: 22
Nuevos: 22
Reutilizar: 0
Actualizar: 0
Conflictos: 0
Pendientes: 1 (FERR REF_PENDIENTE)
Dry-run: cero escrituras
```

## 3. Productos nuevos (propuestos; no escritos)

Ver salida del comando: `R-1008109` … `R-W216` (22 filas) con equipo + REF + LIS documentados.

## 4. Productos existentes reutilizados

Ninguno de la matriz (SKU `R-*` aún no existen).  
Legacy `CRE`/`GLU` Pharmacorp **no** están en la matriz de carga (protegidos / identidad distinta).

## 5. Matriz equipo–reactivo–REF–LIS (documental)

Incluida en `reactivos_matriz_catalogo.py`. Destacados:

- W216 → CPK_MB, MIOG, TROP_I (un producto)
- 1008161 → PROT_U_AZ, PROT_U_24 (un producto)
- Sin ConsumoInsumoExamen

## 6. Duplicados / conflictos

Ninguno detectado en dry-run.

## 7. Pendientes

- FERR: REF pendiente (no carga)

## 8–10. Tests / QC / stock

Ver informe de ejecución en la entrega del asistente (tests inventario + QC).  
Confirmación de diseño: dry-run no llama `create`; no `ConsumoInsumoExamen`; no QC.

## Próximo paso

Tras revisión humana: autorizar `cargar_reactivos_equipo_matriz --apply` **solo** si el dry-run es aceptado.
