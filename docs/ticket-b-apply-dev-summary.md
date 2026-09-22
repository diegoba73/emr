# Ticket B — Apply Docker/dev (2026-09-22)

## Resultado esperado vs real

| Criterio | Resultado |
|----------|-----------|
| 22 productos nuevos | **Sí** (`created 22`) |
| 0 duplicados SKU | **Sí** (`dup_skus False`) |
| CRE/GLU Pharmacorp intactos | **Sí** `(CRE/GLU, PHARMACORP, '')` |
| 0 nuevos ConsumoInsumoExamen | **Sí** (`consumos 2` antes y después) |
| 0 nuevos MovimientoStock | **Sí** (`mov 2` antes y después) |
| Stock nuevos = 0 | **Sí** (`stock0 True`, `lotes_r 0`) |
| FERR excluido | **Sí** (`ferr 0`) |
| Idempotencia 2º `--apply` | **Sí** (`Nuevos: 0`, `Reutilizar: 22`) |
| QC código/expectativas | Sin cambios en esta carga; suites QC OK |
| Producción | **No aplicada** |

## Diff BD (Docker/dev)

| Métrica | Antes | Después |
|---------|-------|---------|
| Reactivos | 2 | 24 |
| SKU `R-*` | 0 | 22 |
| Movimientos | 2 | 2 |
| Consumos | 2 | 2 |
| Lotes (totales) | 12 | 12 (0 en `R-*`) |

Backup: `/home/diego/backups_synesis/synesis_db_ticketb_20260922_004513.dump`  
Log: `docs/ticket-b-apply-dev-report.txt`

## Tests

- `test_cargar_reactivos_matriz` (5): OK  
- `test_inventario_reactivos` + cargar (23): OK  
- `test_qc_gate` + `test_qc_hibrido` (24): OK  

## No Ticket C

Pendiente autorización separada (UI).
