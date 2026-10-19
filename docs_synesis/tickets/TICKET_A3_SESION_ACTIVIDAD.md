# Ticket A3 — `SesionActividad`, backfill, fuente de verdad y espejo transaccional

**Estado:** implementado en código (ver `CIERRE_ETAPA_A3.md`) — **sin merge ni producción**  
**Depende de:** A0+A1 + A2/A2b  
**SoT diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §§1.5–1.6, 1.8 — **este ticket prevalece** donde difiera (espejo mono-sesión histórico)  
**Restricción:** LIMS intocable. **No** modificar validaciones globales de agenda ni permisos para “hacer pasar” A3.  
**Fuera:** A4+ (representación legacy multisesión / `sesion_id` — borrador: `TICKET_A4_ENDPOINTS_SESION.md`), merge, producción.

---

## 0. Decisiones cerradas (pre-implementación)

| # | Decisión |
|---|----------|
| D1 | **SoT reserva:** `SesionActividad.turno`. En **monosesión** (`permite_multi_sesion=False`, único modo operativo), `EstudioComplementario.turno` es espejo **histórico** de `sesión#1.turno`: se conserva aunque el turno esté **REALIZADO** o **CANCELADO**. **No** limpiar la FK por “dejar de estar vigente”. |
| D2 | **“Programado”** (bandejas/UI) se deriva del **estado de la reserva** (p. ej. RESERVADO/CONFIRMADO), **separado** del vínculo histórico `estudio.turno`. |
| D3 | **Representación legacy multisesión** del espejo (§1.6 filas multi) → **diferida a A4**. A3 no habilita ni implementa esa semántica. |
| D4 | **`fecha_realizacion` / `realizado_por`:** en monosesión operativa, el circuito legacy sigue escribiendo en el **estudio**; en la **misma TX** se copian a `SesionActividad` `#1`. Mutaciones cubiertas: create, asignar/agendar turno, `marcar_realizado`, `anular` (y cualquier otra del módulo que hoy mute reserva/realización/anulación). Sin cambio de comportamiento observable del circuito actual. |
| D5 | **Multisesión** deshabilitada en API y admin (como A2). Fixtures de test pueden crear N sesiones para verificar constraints del modelo. |
| D6 | Un **turno** no puede pertenecer a dos sesiones (`UniqueConstraint` en `SesionActividad.turno` donde no null). |
| D7 | `numero_sesion >= 1`, único por indicación (`unique(estudio, numero_sesion)`). |
| D8 | **Eliminación:** no borrar historia clínica. Delete físico de estudio ya bloqueado; sesión no se elimina en flujos normales. Si hace falta baja: soft/`CANCELADA_*` o PROTECT frente a borrados que rompan trazabilidad. Turno no se CASCADE-borra desde sesión (`SET_NULL` o PROTECT según análisis; preferir no perder el Turno). |
| D9 | **Backfill:** estados de sesión coherentes con estado histórico del estudio/turno (ver §5). Idempotente; no sobrescribe datos de sesiones ya existentes. |
| D10 | GET **nunca** escribe ni “repara” espejo/sesión. |
| D11 | Fallo de sync espejo/sesión → **rollback** de toda la operación en la misma TX. |

---

## 1. Objetivo

Modelo `SesionActividad` + backfill 1:1 + sincronización transaccional del espejo mono-sesión **histórico**, preservando 100 % el comportamiento legacy de estudios.

---

## 2. Fuera de alcance

- Lógica de espejo para `permite_multi_sesion=True` (A4).  
- Habilitar multisesión en API/admin.  
- Proc/cirugía operativos (siguen A2).  
- Reprogramar/cancelar sesión avanzada (Etapa B).  
- Cambios LIMS / `turno_estado` global / permisos.

---

## 3. Modelo

| Campo | Tipo | Notas |
|-------|------|--------|
| `estudio` | FK `EstudioComplementario`, `CASCADE`, `related_name='sesiones'` | |
| `numero_sesion` | `PositiveIntegerField` (validators MinValue=1) | |
| `turno` | FK `Turno`, null/blank, **`unique=True`** (o UniqueConstraint excluyendo null) | SoT reserva; un turno ↔ a lo sumo una sesión |
| `fecha_realizacion` | DateTime null | Espejo de sesión; legacy en estudio |
| `realizado_por` | FK user null | Idem |
| `estado_sesion` | choices | Ver §5 backfill |
| timestamps | | |

**Constraints:**  
- `UniqueConstraint(estudio, numero_sesion)`  
- `UniqueConstraint(turno)` where `turno IS NOT NULL`  

**Delete:** no exponer destroy de sesión en API A3. `on_delete` turno → `SET_NULL` (conserva sesión e historia; el Turno puede vivir o no según otros flujos — no inventar cancelación global).

### Estados de sesión (mínimos)

| `estado_sesion` | Uso |
|-----------------|-----|
| `PROGRAMADA` | Tiene turno en RESERVADO/CONFIRMADO (o estudio CONFIRMADO con turno) |
| `REALIZADA` | Estudio/sesión realizada (`fecha_realizacion` o estudio REALIZADO+) |
| `CANCELADA` | Estudio ANULADO y/o turno CANCELADO (vínculo histórico al turno se **conserva**) |
| `PENDIENTE` | Sin turno / estudio SOLICITADO sin reserva |

(Exact mapping en backfill §5; nombres pueden ajustarse en código si se documentan.)

---

## 4. Espejo mono-sesión (A3)

```
sincronizar_espejo_turno(estudio):
  assert not permite_multi_sesion or (solo fixtures / no camino API)
  sesion = sesión #1
  estudio.turno_id = sesion.turno_id   # siempre, aunque turno CANCELADO/REALIZADO
  # NO nullificar por “no vigente”
```

“Programado” para bandejas = consulta de `turno.estado in (RESERVADO, CONFIRMADO)` (o flag derivado en serializer **read-only**), no ausencia de FK.

---

## 5. Backfill

Para cada estudio **sin** sesión `#1`:

1. Crear `SesionActividad(numero_sesion=1, turno_id=estudio.turno_id, fecha_realizacion=…, realizado_por=…)`.  
2. `estado_sesion` coherente:
   - estudio `ANULADO` → `CANCELADA`
   - estudio en `REALIZADO|INFORMADO|VALIDADO|ENTREGADO` → `REALIZADA`
   - tiene turno y turno.estado en RESERVADO/CONFIRMADO → `PROGRAMADA`
   - tiene turno CANCELADO/REALIZADO → `CANCELADA` o `REALIZADA` según turno/estudio (priorizar estado estudio si ya avanzó)
   - else → `PENDIENTE`
3. **No** modificar `estudio.turno` ni demás FKs legacy.  
4. Idempotente: si `#1` existe, **no** sobrescribir sus campos.

---

## 6. Mutaciones (misma TX)

| Flujo | Comportamiento |
|-------|----------------|
| `crear_estudio` | Crear sesión `#1` PENDIENTE; espejo null |
| `asignar_turno` / `agendar` | Turno → sesión `#1`; `estado_sesion=PROGRAMADA`; `sincronizar_espejo`; estudio.turno como hoy |
| `marcar_realizado` | Como hoy en estudio; copiar `fecha_realizacion`/`realizado_por` a `#1`; `estado_sesion=REALIZADA` |
| `anular` | Como hoy en estudio; `#1.estado_sesion=CANCELADA`; **no** borrar `turno` en sesión ni espejo |
| GET/list/detail | Solo lectura; **cero** writes |

Si cualquier paso de sync falla → rollback completo.

Concurrencia: `select_for_update` del estudio (y sesión `#1`) en asignar_turno para evitar dos asignaciones divergentes.

---

## 7. Criterios de aceptación

- [x] Backfill: conteos; vínculos turno históricos (incl. cancelados/realizados) en sesión y estudio.  
- [x] Reejecutar backfill no pisa.  
- [x] Create → sesión 1.  
- [x] Realizar actualiza sesión + legacy.  
- [x] Fallo sync → rollback.  
- [x] Dos asignaciones concurrentes no dejan divergencia.  
- [x] GET no muta.  
- [x] Multisesión sigue off en API/admin.  
- [x] Diff `laboratorio/` vacío; sin cambios de permisos/validaciones globales.

---

## 8. Pruebas obligatorias

| Prueba | Esperado |
|--------|----------|
| Turno REALIZADO/CANCELADO conserva vínculo histórico estudio↔sesión | FK intactas |
| `marcar_realizado` actualiza sesión + campos legacy | Igualdad de fechas/usuario |
| Fallo sync revierte operación | Sin cambio parcial |
| Asignaciones concurrentes | Una gana; sin divergencia espejo/sesión |
| Backfill conserva campos/relaciones/estados; repetición no sobrescribe | |
| GET no modifica datos | timestamps/FKs iguales |
| Constraints: dos sesiones mismo turno | IntegrityError |
| `numero_sesion` único / >=1 | |

---

## 9. Compatibilidad endpoints

Mono-sesión: `asignar-turno` / `agendar-turno` sin `sesion_id` (comportamiento actual). Multisesión / espejo §1.6 multi → **A4**.
