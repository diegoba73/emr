# Cierre — Etapa A3 (`SesionActividad`)

**Fecha:** 2026-10-16  
**Estado:** aceptado en código; **sin merge ni producción**  
**Dependencia:** A0+A1 + A2/A2b (`estudios.0006`)  
**Ticket:** `docs_synesis/tickets/TICKET_A3_SESION_ACTIVIDAD.md`  
**Diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §1.6 (mono histórico; multi → A4)  
**Paquete:** `/home/diego/proyectos/emr-a0-compare-artifacts/a3_package/`

---

## Dependencias

| Prerrequisito | Motivo |
| --- | --- |
| A0 cerrado | Baseline no-regresión LIMS/agenda |
| A1 `clasificacion_quirurgica` | Catálogo |
| A2/A2b `tipo_actividad` + altas off | Indicación ESTUDIO; multi off |
| LIMS intocable | Diff A3 vacío en `laboratorio/` |

Orden de apply: **A0+A1 → A2 → A3**.

---

## Entregable A3

- Modelo `SesionActividad` + constraints (`estudio`+`numero_sesion`; `turno` unique where not null).
- Migración `estudios.0007_sesion_actividad_a3` + backfill 1:1 idempotente (no sobrescribe).
- SoT: `SesionActividad.turno`; espejo mono **histórico** `estudio.turno = sesión#1.turno` (conserva REALIZADO/CANCELADO).
- Dual-write `fecha_realizacion` / `realizado_por` en la misma TX (`crear`, asignar/agendar, `marcar_realizado`, anular).
- `select_for_update` en `asignar_turno_estudio` anti-divergencia concurrente.
- GET sin writes. Multisesión API/admin sigue off; fixtures de modelo OK.

---

## Evidencias — suite A3

| Prueba | Resultado |
| --- | --- |
| `test_crear_estudio_crea_sesion_uno` | PASSED |
| `test_turno_realizado_conserva_vinculo_historico` | PASSED |
| `test_turno_cancelado_conserva_vinculo_historico` | PASSED |
| `test_sync_fallo_revierte_asignacion` | PASSED |
| `test_asignaciones_concurrentes_sin_divergencia` | PASSED |
| `test_turno_no_puede_pertenecer_a_dos_sesiones` | PASSED |
| `test_numero_sesion_unico_y_gte_uno` | PASSED |
| `test_backfill_conserva_e_idempotente` | PASSED |
| `test_get_no_modifica_datos` | PASSED |

Comando: `pytest estudios/tests/test_a3_sesion.py` → **9 passed**.  
Regresión A2 + `estudios/tests/test_api.py`: **OK**.

---

## Fallos conocidos — dos buckets (no mezclar)

### Bucket 1 — Suite A0 (LIMS / turnos globales)

Comparativa: `results_a3.txt` vs `results_a2_post.txt` (artefactos en `emr-a0-compare-artifacts/`).  
Resultado: **idénticos**; **sin regresiones nuevas** atribuibles a A3. **No corregidos** (LIMS intocable; no tocar permisos/agenda global).

| Suite A0 | A2 post | A3 | Fallo |
| --- | --- | --- | --- |
| LIMS_Authorization | EXIT=0 | EXIT=0 | — |
| LIMS_Flujo_critico | EXIT=1 | EXIT=1 | 2× `fecha_programada_toma` 400 |
| Turnos_solapamiento | EXIT=0 | EXIT=0 | — |
| Turnos_estado_turnos | EXIT=1 | EXIT=1 | 2× lab 403 vs 404 esperado |

Los cuatro fallos A0:

1. `test_flujo_critico_lims_microbiologia_final_validado_informado`
2. `test_flujo_critico_lims_muestra_resultado_microbiologia`
3. `test_laboratorio_no_puede` (iniciar atención)
4. `test_laboratorio_no_puede_cancelar`

### Bucket 2 — Estudios (fuera de A0): `test_asignar_turno_estudio_rechaza_sala_ocupada`

**No forma parte de los 4 fallos A0.** Es un fallo del módulo `estudios` al invocar `validar_reserva` con slot de 30′ frente a duración default 20′, más desajuste DRF vs Django `ValidationError` en el `pytest.raises` del test.

**Evidencia comparativa HEAD vs A3** (corrida dedicada; no se tocó agenda global):

- Artefacto: `/home/diego/proyectos/emr-a0-compare-artifacts/sala_ocupada_head_vs_a3.txt`
- Script: `_tmp_a0_compare/compare_sala_ocupada.sh`
- HEAD (`1ecd0df…`): **FAILED** — `validar_reserva` → duración 20′ (`EXIT_HEAD=1`)
- Working tree con A3: **FAILED** — mismo mensaje y misma causa (`EXIT_A3=1`)

Conclusión: **preexistente en HEAD**; A3 **no introduce ni altera** el comportamiento. Fuera de alcance A3 corregirlo (haría falta ajustar el test o la agenda global; lo segundo está prohibido para este ticket).

---

## Fuera de este cierre

- A4+ (`sesion_id`, espejo multisesión) — ticket de revisión: `TICKET_A4_ENDPOINTS_SESION.md`
- Habilitar multisesión o proc/cirugía operativos
- Merge / producción / cambios LIMS / validaciones globales de agenda
