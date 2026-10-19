# Cierre — Etapa A2 / A2b

**Fecha:** 2026-10-16  
**Estado:** aceptado en código (evidencias de cierre abajo); **sin merge ni producción**  
**Dependencia obligatoria:** paquete **A0+A1** aplicado/presente (`catalogos.0010`, clasificación en `ProcedimientoCatalogo`, checklist A0).  
**SoT ticket:** `docs_synesis/tickets/TICKET_A2_A2b_ESTUDIOS_PROCEDIMIENTOS.md`  
**Diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` (sección A2)

---

## Dependencia A0+A1

| Prerrequisito | Motivo |
|---------------|--------|
| A0 cerrado (verificación comparativa) | Baseline de no-regresión LIMS/agenda; 4 fallos HEAD documentados, no “arreglados” |
| A1 `clasificacion_quirurgica` + migración `catalogos.0010` | FK `procedimiento_catalogo` y correspondencia exacta tipo↔snapshot |
| LIMS intocable | Diff A2 vacío en `laboratorio/`; WIP LIMS ajeno no mezclado |

Orden de apply sugerido: **A0+A1** → **A2/A2b**.

---

## Entregable A2/A2b (resumen)

- Campos aditivos en `EstudioComplementario` + `practica` nullable (EMR).
- Migración `estudios.0006_estudio_tipo_actividad_a2` + backfill idempotente.
- Altas operativas `PROCEDIMIENTO`/`CIRUGIA` y `permite_multi_sesion=True` **deshabilitadas**.
- PATCH protege tipo/FK/snapshot/multi; circuito legacy solo `ESTUDIO`.
- A2b: `POST .../corregir-clasificacion-snapshot/` (admin, motivo, TX+audit atómicos).

Paquete: `/home/diego/proyectos/emr-a0-compare-artifacts/a2_package/`.

---

## Evidencias de cierre (pruebas)

### Migración / backfill (conservación + idempotencia)

| Prueba | Qué cubre | Resultado |
|--------|-----------|-----------|
| `estudios/tests/test_a2_actividad.py::test_backfill_idempotente_no_pisa_proc` | Conteo estable; conserva `paciente`, `tipo_estudio`, `practica`, `origen`, `descripcion_clinica`, `creado_por`, `estado` en legacy; **no** pisa fila `PROCEDIMIENTO` controlada; **doble** ejecución del backfill | **PASSED** (corrida cierre) |

### A2b — rollback si falla auditoría

| Prueba | Qué cubre | Resultado |
|--------|-----------|-----------|
| `estudios/tests/test_a2_actividad.py::test_a2b_rollback_si_falla_auditoria` | `AuditEvent.objects.create` falla → excepción; snapshot **sin** cambio; sin evento de corrección | **PASSED** (corrida cierre) |

### Suite A2 (referencia)

`pytest estudios/tests/test_a2_actividad.py` (+ legacy/A1 en implementación): ver corrida de cierre en este cierre.

### A0 post-A2 (sin corregir LIMS)

Mismos **4 fallos preexistentes** en HEAD documentados en `CIERRE_ETAPA_A0_A1.md` / checklist A0:

1–2. `test_lims_flujo_critico` → 400 `fecha_programada_toma`  
3–4. lab cancelar/iniciar-atención → 403 vs 404  

**No corregidos** en A2.

---

## Fuera de este cierre

- A3+ (sesiones / espejo / `sesion_id`)  
- Habilitar altas proc/cirugía o multisesión  
- Merge / producción / cambios LIMS
