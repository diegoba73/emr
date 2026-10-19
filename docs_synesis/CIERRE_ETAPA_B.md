# Cierre — Etapa B (Reprogramar / cancelar actividad)

**Fecha:** 2026-10-16  
**Estado:** implementado en código; **sin merge ni producción**  
**Dependencia:** A0–A6  
**Ticket:** `docs_synesis/tickets/TICKET_B_REPROGRAMAR_CANCELAR.md`  
**Paquete:** `/home/diego/proyectos/emr-a0-compare-artifacts/b_package/`  
**Migración:** `estudios.0008_historial_turno_sesion_b`

---

## Entregable

1. **Cancelación:** `anular` / `anular_estudio` solo en `SOLICITADO`/`CONFIRMADO`; libera reserva vigente (`CANCELADO`); motivo obligatorio; docs/vínculos conservados. Rectificación documental intacta.
2. **Historial:** `HistorialTurnoSesionActividad` en `estudios/` (PROTECT); sin campos nuevos en `Turno`.
3. **Reprogramar:** turno nuevo + cancelar anterior + historial + sync espejo + auditoría en **una TX**; API `POST …/reprogramar-turno/` + UI en detalle.
4. **Agenda general:** guarda en `cancelar_turno` / `reprogramar_turno` para turnos vinculados a estudios; bypass `desde_modulo_estudios=True`.
5. **Duración:** `estudios/disponibilidad.py` (inicio/fin variable); `validar_reserva` de consultorio intacta.
6. **Concurrencia:** orden estudio → sesión → turno → médico → recurso; excluye reserva propia; rollback total si falla.
7. **Alcance:** multi/proc/cirugía off; LIMS intocable.

---

## Evidencias de pruebas

| Suite | Resultado |
| --- | --- |
| `estudios/tests/test_b_reprogramar_cancelar.py` | **14 passed** (incluye verificaciones de cierre abajo) |
| `test_asignar_turno_estudio_rechaza_sala_ocupada` (sobre B) | **passed** |
| A3+A4+A5+API+B (previas) | 64 passed |
| Frontend `modules/estudios` | 7 passed |

UI: anular con motivo + reprogramar desde `EstudioComplementarioDetalle` (permisos actuales de escritura / asignar turno). Error de disponibilidad visible; reserva anterior conservada.

---

## Verificaciones de cierre (post-aceptación provisional)

### 1. `desde_modulo_estudios` no activable por API/móvil

- Views turnos/móvil **no** leen el flag de body ni query; solo kwarg interno del servicio de estudios.
- Pruebas: `test_api_desde_modulo_estudios_no_activable_por_payload_ni_query`, `test_movil_reprogramar_no_acepta_flag_desde_modulo` → **passed**.

### 2. Guarda + turnos históricos de reprogramación

- `_turno_vinculado_modulo_estudios` contempla espejo, `SesionActividad.turno` y `HistorialTurnoSesionActividad` (anterior/nuevo).
- Consulta histórica preservada (historial y FKs intactos); solo se bloquean mutaciones genéricas cancelar/reprogramar.
- Prueba: `test_guarda_cubre_turno_historico_de_reprogramacion` → **passed**.

### 3. `test_asignar_turno_estudio_rechaza_sala_ocupada` sobre B

- Ejecutado explícitamente en el mismo run que la suite B: **passed**.
- Con el helper `estudios/disponibilidad` (sin exigir duración fija de consultorio) el rechazo es por **ocupación/buffer de sala**, no por el check de slot de `validar_reserva`.
- `medicos.agenda.validar_reserva` (consultorio) permanece intacta.

---

## Fallos preexistentes (no corregidos en B)

### A0 — `results_b.txt` ≡ `results_a5.txt`

| Suite | EXIT A5 | EXIT B |
| --- | --- | --- |
| LIMS_Authorization | 0 | 0 |
| LIMS_Flujo_critico | 1 | 1 |
| Turnos_solapamiento | 0 | 0 |
| Turnos_estado_turnos | 1 | 1 |

4 fallos documentados (LIMS flujo crítico ×2; `test_laboratorio_no_puede` / `test_laboratorio_no_puede_cancelar` 403 vs 404). Consola: `run_a0_b_console.txt`.

---

## Fuera de este cierre

- Etapa C+ (ticket de revisión: `tickets/TICKET_C_PROCEDIMIENTOS_NO_QUIRURGICOS.md` — **no implementado**)  
- Merge / producción / cambios LIMS  
- Multisesión operativa / cirugías  
- “Dejar pendiente de nueva fecha”
