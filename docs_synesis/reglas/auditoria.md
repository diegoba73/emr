# Reglas — Auditoría (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**SoT operativo:** `DOC_PERMISOS_AUDITORIA.md`, `auditoria/audit_service.py`, `auditoria/snapshot.py`, `docs/auditoria-hardening.md` (complemento arquitectura).

---

## Propósito

Toda mutación **clínicamente o analíticamente relevante** debe ser **reconstruible**: quién, qué, cuándo, desde qué estado, con evidencia suficiente y sin filtrar secretos.

---

## Principios **[RECTOR]**

1. **Append-only** para `AuditEvent` (no UPDATE/DELETE vía ORM estándar).
2. Persistencia en **`transaction.on_commit`** cuando la operación de negocio es atómica.
3. **Sanitización** de claves sensibles y límites de tamaño en JSON.
4. No auditar recursivamente la tabla de auditoría (blacklist).
5. Snapshots de archivos/binarios como marcadores, no contenido crudo.

---

## Eventos mínimos auditables

| Dominio | Evento | Estado |
|---------|--------|--------|
| Paciente | creado / modificado demográficos | **[OBJETIVO]** cobertura completa |
| Orden LIMS | creada / cancelada / cambio estado | **[IMPLEMENTADO]** vía `solicitud_estado` + `log_*` |
| Muestra | tomada / recibida / rechazada / en proceso / … | **[IMPLEMENTADO]** `EventoMuestra` + `AuditEvent` |
| Resultado | cargado / validado (bulk) | **[IMPLEMENTADO]** metadata en `cargar-resultados` / `validar` |
| Resultado | corregido post-validación | **[OBJETIVO]** |
| Informe micro | emitido / validado / anulado | **[IMPLEMENTADO]** B3.4 |
| Permisos | cambio rol/grupos | **[OBJETIVO]** |
| IA | sugerencia mostrada / aceptada / rechazada | **[OBJETIVO]** |
| Atención | alta / cierre / registrar consulta | **[IMPLEMENTADO]** parcial en views/servicio |

---

## Metadata esperada (LIMS ejemplo) **[IMPLEMENTADO]**

- `solicitud_id`, `numero_solicitud`, `resultado_id`, `muestra_id`, `codigo_barra`
- Transiciones: `estado_anterior`, `estado_nuevo`, `accion`
- B4.1: valores numéricos/patológicos en metadata de update (sin PHI libre innecesaria)

---

## Lectura de auditoría

- `GET /api/auditoria/events/` — solo **admin** / staff / superuser (`IsAuditAdmin`).
- Header `X-Request-ID` por request (`RequestContextMiddleware`).

---

## Invariantes

Ver `DOC_INVARIANTES.md` (AUD1–AUD4).

---

## Deuda conocida

- `validar` usa `bulk_update` → auditoría “before” incompleta en resultados.
- Cobertura desigual entre views legacy (`api/views`) y rutas activas.
- Privilegio REVOKE a nivel PostgreSQL: **[OBJETIVO]** (`auditoria-hardening.md` §5).

---

## Pendientes de validación

- [ ] Inventario de views sin `log_create`/`log_update` en altas sensibles.
- [ ] Test de rollback sin `AuditEvent` huérfano (`test_auditoria_hardening`).
