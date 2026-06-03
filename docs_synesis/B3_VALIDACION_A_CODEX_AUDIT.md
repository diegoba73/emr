# B3-frontend-validación-A — Paquete auditoría Codex

**Estado:** [VALIDADO] — junio 2026 (PostgreSQL + pytest + Jest focal).

## Regla de negocio

| Concepto | Valor |
|----------|--------|
| Estados que bloquean operación técnica | `CANCELADO`, `VALIDADO`, `INFORMADO` |
| Constante servicio | `ESTADOS_BLOQUEAN_OPERACION_MICRO` en `laboratorio/microbiologia_estado.py` |
| Modelo `EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION` | Sin cambio — solo `CANCELADO` en `clean()` |
| Transición permitida en estudio cerrado técnico | `VALIDADO` → `INFORMADO` vía `aplicar_marcar_estudio_informado` |
| No cerrado en esta fase | `LISTO_PARA_VALIDAR` |

## Backend — puntos de control

- `assert_estudio_micro_operable(estudio)` antes de mutaciones en `microbiologia_estado.py`.
- `_guard_estudio_micro_operable_entity` en PATCH de `views_microbiologia.py`.
- `aplicar_marcar_estudio_informado`: exige `estudio.estado == VALIDADO`; **no** llama `assert_estudio_micro_operable`.
- Operación bloqueada: HTTP 400, sin entidades hijas nuevas, sin `AuditEvent` CREATE de éxito (test `test_validado_bloquea_operaciones_tecnicas`).

## Frontend — puntos de control

- `limsAccess.ts`: `isMicroEstudioCerrado`, `canOperateMicroEstudioTecnico`, `canMarcarMicroEstudioInformado`.
- `MicrobiologiaEstudioDetalle.tsx`: alerta + `canOpEstudio` en tabs operativas.
- Datos históricos: listados/tablas siguen visibles en estados cerrados.

## Tests de referencia

| Suite | Resultado reportado |
|-------|---------------------|
| `TestEstudioMicroCerradoOperacionAPI` | 4 passed |
| `test_microbiologia_*.py` | 165 passed |
| Regresión LIMS | 315 passed |
| `limsAccess.test.ts` | 8 passed |

## Commits

- Frontend: `35d1edc`
- Padre: `75d56b2`

## Hallazgos conocidos (no bloquean cierre A)

- Detalle micro carga listados globales y filtra en cliente — [GAP] filtros `estudio_id` en API micro.
- Modelo `clean()` solo conoce `CANCELADO`; cierre `VALIDADO`/`INFORMADO` depende del servicio.
