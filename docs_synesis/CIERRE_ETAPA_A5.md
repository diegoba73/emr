# Cierre — Etapa A5 (UI bandejas / “Estudios y procedimientos”)

**Fecha:** 2026-10-16  
**Estado:** aceptado en código; **sin merge ni producción**  
**Dependencia:** A0+A1 + A2–A4  
**Ticket:** `docs_synesis/tickets/TICKET_A5_UI_BANDEJAS.md`  
**Paquete:** `/home/diego/proyectos/emr-a0-compare-artifacts/a5_package/`

---

## Entregable

- Nombre visible **“Estudios y procedimientos”** (sidebar, listado, header, Dashboard). Ruta `/estudios-complementarios` intacta.
- Bandejas server-side (`bandeja=` **antes** de paginar) + `GET …/bandejas-resumen/` (mismos permisos, `search` y `practica`).
- Matriz (realización/anulación prevalecen sobre la reserva):

| Bandeja | Criterio |
| --- | --- |
| Pendiente de programar | `SOLICITADO` / `CONFIRMADO` sin reserva vigente |
| Programados | `SOLICITADO` / `CONFIRMADO` con turno `RESERVADO` / `CONFIRMADO` |
| Documentación pendiente | `REALIZADO` / `INFORMADO` |
| Pendiente de entrega | `VALIDADO` |
| Finalizados | `ENTREGADO` |
| Anulados | `ANULADO` |
| Todos | sin filtro de bandeja |

- Sin controles de proc/cirugía/multisesión. Sin writes en GET. Acciones, búsqueda, archivos y permisos conservados.

---

## Evidencias de pruebas (efectivas)

| Suite | Resultado |
| --- | --- |
| `estudios/tests/test_a5_bandejas.py` | 5 passed |
| A5 + A4 + A3 (combinados) | 27 passed |
| A2 + `estudios/tests/test_api.py` | 39 passed |
| Frontend `modules/estudios` | 7 passed (`bandejas.test.ts` + `permissions.test.ts`) |

Flujo: `test_flujo_completo_bandejas` — crear → programar → realizar → informe → emitir → validar → entregar.

---

## Fallos preexistentes (no corregidos en A5)

### Bucket 1 — Suite A0 (exactamente 4 fallos)

Fuente: `emr-a0-compare-artifacts/results_a5.txt` vs `results_a4.txt` — **idénticos**; sin regresiones nuevas.

| Suite A0 | EXIT A4 | EXIT A5 | Fallos (nombres) |
| --- | --- | --- | --- |
| LIMS_Authorization | 0 | 0 | — |
| LIMS_Flujo_critico | 1 | 1 | `test_flujo_critico_lims_microbiologia_final_validado_informado`; `test_flujo_critico_lims_muestra_resultado_microbiologia` (400 `fecha_programada_toma`) |
| Turnos_solapamiento | 0 | 0 | — |
| Turnos_estado_turnos | 1 | 1 | `test_laboratorio_no_puede`; `test_laboratorio_no_puede_cancelar` (obtenido 403, esperado 404) |

### Bucket 2 — Estudios (fuera de A0; 1 fallo preexistente)

| Prueba | Evidencia |
| --- | --- |
| `estudios/tests/test_validacion_sala.py::test_asignar_turno_estudio_rechaza_sala_ocupada` | HEAD ≡ A3: `sala_ocupada_head_vs_a3.txt` (`EXIT_HEAD=1`, `EXIT_A3=1`). Causa: `validar_reserva` duración 20′ vs slot 30′ del test. A5 no toca agenda global. |

---

## Fuera de este cierre

- A6 (documentación consolidada Etapa A)  
- Etapa B+ (reprogramar/cancelar avanzado)  
- Habilitar proc/cirugía/multi; merge / producción / LIMS
