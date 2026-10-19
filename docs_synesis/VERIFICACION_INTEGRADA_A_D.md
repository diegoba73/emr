# Verificación integrada A–D (entorno de pruebas)

**Fecha:** 2026-10-16  
**Entorno:** Docker local (`emr_postgres` / `emr_backend:8000` / `emr_frontend:3000`)  
**Datos:** paciente ficticio `ADFICTICIO, VERIF` DNI `90999111`; catálogo aditivo `VERIF_AD_PROC_*_FICTICIO`  
**LIMS:** no tocado en esta verificación ni en el paquete D  
**E/F / merge / producción:** no aplicados  

## Veredicto

**PENDIENTE**

Motivo: los circuitos funcionales A–D pasaron contra la API del entorno de pruebas (misma base que usa la UI), pero el recorrido **completo** en navegador (alta vía Autocomplete + todos los pasos UI) no quedó cerrado. Lo verificado en UI es parcial (listado/bandejas/detalle + cierre secretaría).

---

## 1. Circuitos funcionales (API live, datos ficticios)

Script: `/tmp/verif_ad_django.py` → `/tmp/verif_ad_django_out.txt`  
**SUMMARY_FAILS=0 TOTAL=44**

| Recorrido | Resultado | Evidencia (sin PHI) |
| --- | --- | --- |
| Estudio: alta → programar → reprogramar → realizar → informe → emitir/validar → entregar | PASS | ids ficticios en log; `practica=IMAGEN_US` |
| Procedimiento sin sala: realizar → informe → validar → entregar | PASS | `atencion=None` |
| Procedimiento con sala: realizar → doc completo | PASS | `atencion` creada |
| Cirugía sin turno: realizar (anestesia real, protocolo pendiente) → doc → secretaría cierra → entregar → rectificar → bloqueo entrega → nuevo cierre → entregar | PASS | historial cierres/entregas ≥2 |
| Cirugía con turno: asignar → reprogramar → realizar → cerrar secretaría → entregar | PASS | |
| Cancelación previa: ANULADO + turno CANCELADO | PASS | tras fix respuesta API |

---

## 2. Permisos secretaría (UI + backend)

| Check | Resultado |
| --- | --- |
| Backend (política A–D original): emitir/validar/rectificar → **403** | PASS en esa corrida |
| Backend: cerrar con protocolo validado → **200** | PASS |
| UI (`secretaria1` / Laura): detalle `#27` VALIDADO — botón **Cerrar cirugía** (sin Emitir/Validar/Rectificar en esa corrida) | PASS |
| **Nota post-verificación:** política actualizada — secretaría es operador completo del módulo (alta/edición/emitir/validar/rectificar). Ver `reglas/usuarios-y-permisos.md`. | — |
| FE helpers `permissions.ts` + tests `modules/estudios` | PASS (7 tests) |

---

## 3. Build / typecheck / tests FE

| Check | Resultado |
| --- | --- |
| `npx tsc --noEmit` | PASS (exit 0) |
| `CI=true npm test -- --testPathPattern=modules/estudios` | PASS 7/7 |
| `docker exec emr_frontend npm run build` | PASS (build folder ready) |

Consola/red en UI: detalle y cierre secretaría sin errores de red observados en el recorrido parcial.

---

## 4. Migraciones / diff / A0 / WIP

| Check | Resultado |
| --- | --- |
| Migraciones `estudios.0006`…`0010` aplicadas en DB prueba | PASS |
| `catalogos.0010_procedimientocatalogo_clasificacion_quirurgica` presente | PASS |
| A0 `results_d` ≡ `results_c` (fallos preexistentes) | PASS — mismos EXIT/FAILED LIMS Flujo + Turnos estado |
| Paquete D sin `laboratorio/` | PASS (`d_patch_paths.txt`) |
| WIP LIMS preexistente en working tree (`laboratorio/qc_*`, etc.) | **Separado** — no modificado en esta verificación |
| Conservación de datos | PASS — cambios aditivos; anulaciones/cierres sobre registros ficticios de verif |

---

## 5. Defecto A–D encontrado y corregido

**Anular devolvía estado/turno stale** (`CONFIRMADO` en response aunque DB=`ANULADO` y turno=`CANCELADO`).

- Causa: `views.anular` serializaba la instancia pre-`select_for_update` del service.
- Fix: usar la instancia retornada por `anular_estudio` (+ context request).
- Regresión: `test_api_anular_responde_anulado_y_libera_turno` — **1 passed**.

Archivo: `estudios/views.py` (`anular`).

---

## 6. Browser — estado honesto

| Ítem | Estado |
| --- | --- |
| Login admin / secretaría, listado, bandejas, filtro paciente ficticio, detalle | Hecho |
| Cierre cirugía como secretaría + aparición Entregar | Hecho |
| Alta UI vía Autocomplete paciente (todos los circuitos clic a clic) | **No cerrado** — typing en Autocomplete MUI no setea valor de forma fiable en la herramienta |
| Sustituto funcional | APIClient contra el mismo backend/DB de prueba |

Por eso el veredicto global es **PENDIENTE**, no **cumple**.

---

## Fuera de alcance (respetado)

- Etapas E/F  
- Merge / producción  
- Cambios LIMS (directos o indirectos)  
- “Arreglar” fallos A0 preexistentes  
