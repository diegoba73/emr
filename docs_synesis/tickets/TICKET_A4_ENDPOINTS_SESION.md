# Ticket A4 — Endpoints legacy con `sesion_id`, espejo multisesión y rechazo de ambigüedad

**Estado:** implementado en código (ver `CIERRE_ETAPA_A4.md`) — **sin merge ni producción**  
**Depende de:** A0+A1 + A2/A2b + **A3 cerrado**  
**SoT diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §1.6 — **este ticket prevalece**  
**Restricción:** LIMS intocable (directa e indirectamente). Sin A5+, merge ni producción.

---

## 0. Decisiones cerradas

| # | Decisión |
| --- | --- |
| D1 | Multi (`permite_multi_sesion=True`, solo fixtures): mutaciones de **asignación de turno** exigen `sesion_id` explícito. **No** inferir sesión. |
| D2 | Validar **primero acceso a la indicación**. Sesión inexistente o de otra indicación → **mismo 400 genérico**: `Sesión no válida para esta indicación` (sin revelar info ajena). |
| D3 | **Monosesión:** sin `sesion_id` → sesión `#1` (A3). Con `sesion_id` → debe ser la **PK real** de la sesión `#1` (no el literal `1`). |
| D4 | Ambiguo = multi **sin** `sesion_id` → 400. Un **espejo null no impide** operar si `sesion_id` identifica inequívocamente una sesión válida de la indicación. |
| D5 | Espejo legacy multi (misma TX; **nunca** borrar `SesionActividad.turno`): 0 vigentes → `null`; exactamente 1 → ese turno; \>1 → `null`. Vigente = turno RESERVADO/CONFIRMADO. **Monosesión** conserva exactamente el contrato histórico A3 (`estudio.turno = sesión#1.turno` siempre). |
| D6 | “Programado” se deriva del estado de la reserva, no del espejo. |
| D7 | Permisos: reutilizar los del módulo estudios. Sin roles nuevos ni matriz LIMS. |
| D8 | Mientras no haya soporte completo: multi **deshabilitada** en altas API/admin. **Realización, informes y anulación legacy** rechazan indicaciones multi **sin modificar datos**, aunque reciban `sesion_id`. **No** anulación parcial ni realización por sesión en A4. Mono intacto. |
| D9 | Mutación + sync + auditoría en **misma TX**; fallo → rollback. GET no repara. Bloqueos: **indicación → sesión**. |
| D10 | Auditoría assign: atómica en TX + metadata `sesion_id` / `numero_sesion`. |
| D11 | `agendar-turno`: si crea indicación nueva → monosesión (A2/A3). El endpoint **ya** admite `estudio_id` existente (SOLICITADO sin turno) y delega a `asignar_turno`; A4 solo propaga `sesion_id` en ese camino. **No** agregar soporte nuevo sobre otras formas de indicación existente. |

---

## 1. Objetivo

Contrato endpoints + espejo multi (fixtures) + rechazo de acciones legacy no soportadas en multi; monosesión 100 % A3.

---

## 2. Fuera de alcance

- LIMS; habilitar multi operativo; realización/informes/anulación por sesión; A5+; merge/prod; arreglar fallos A0 / `sala_ocupada` vía agenda global.

---

## 3. Contrato endpoints

| Flujo | Mono | Multi (fixture) |
| --- | --- | --- |
| `asignar-turno` | A3; `sesion_id` opcional = PK de `#1` | Exige `sesion_id`; pertenencia genérica; asigna; espejo D5 |
| `agendar-turno` | Alta nueva → mono; existente vía `estudio_id` → igual que asignar (+ `sesion_id`) | Solo si `estudio_id` multi (fixture); mismas reglas que asignar |
| `marcar-realizado` / anular / informes | A3 intacto | **Rechazo sin escrituras** (aunque venga `sesion_id`) |

---

## 4. Espejo

```
si not permite_multi_sesion:
    estudio.turno_id = sesión#1.turno_id   # histórico A3
else:
    vigentes = sesiones cuyo turno.estado in (RESERVADO, CONFIRMADO)
    0 → null; 1 → ese turno_id; >1 → null
    # no tocar SesionActividad.turno por vigencia
```

---

## 5. Pruebas obligatorias

- Mono sin/`con` PK `#1`; mono con `sesion_id` ajeno → 400 genérico  
- Multi sin `sesion_id` → 400; ajeno → 400 genérico; propio → assign + espejo D5  
- Espejo 0/1/2 vigentes; FKs sesión conservadas  
- Espejo null + `sesion_id` válido → assign OK  
- Concurrente: dos assigns a **distintas** sesiones misma indicación → espejo final coherente D5  
- Permisos assign; multi realizar/anular/informe → rechazo sin escrituras  
- Rollback si falla auditoría en assign  
- GET no escribe; diff `laboratorio/` vacío  

---

## 6. Entregables

Diff exclusivo A4 (sobre A3), regresión A3/A2, A0 comparativa, `CIERRE_ETAPA_A4.md`. Sin merge/prod.
