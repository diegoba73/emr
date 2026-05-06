# Auditoría (capa 1)

Esta app implementa la **primera capa transversal** de auditoría del EMR+LIMS.

## Objetivo
- Registro **append-only** de eventos críticos (CREATE/UPDATE/DELETE y acciones de estado).
- Captura de:
  - actor (usuario)
  - entidad (tipo/id/representación)
  - before_state / after_state (JSON)
  - request_id / ip / user_agent
  - metadata contextual

## Componentes
- `auditoria.models.AuditEvent`: modelo append-only (bloquea UPDATE/DELETE).
- `auditoria.middleware.RequestContextMiddleware`: genera `request_id` y captura `ip`/`user_agent` (header `X-Request-ID`).
- `auditoria.audit_service`: helpers reutilizables `log_create/log_update/log_delete/log_event` (best-effort; no rompe el flujo principal). Dentro de `transaction.atomic()`, la escritura usa `transaction.on_commit` para no registrar eventos cuando la operación principal hace rollback.
- `auditoria.snapshot.safe_model_snapshot`: snapshot minimalista sin recursión (solo campos concretos, FK como `_id`).
- API readonly:
  - `GET /api/auditoria/events/`
  - `GET /api/auditoria/events/{id}/`

## Filtros API
En `GET /api/auditoria/events/`:
- `entity_type` (iexact)
- `entity_id` (exact)
- `actor` (actor_id)
- `action` (iexact)
- `fecha_desde` / `fecha_hasta` (ISO datetime sobre `timestamp`)
- `request_id` (exact)

Para endurecimiento (rollback, sanitización de datos sensibles, append-only y límites de snapshot): ver **`docs/auditoria-hardening.md`**.

## Permisos
Solo lectura para:
- superuser
- staff
- `rol == 'admin'`

