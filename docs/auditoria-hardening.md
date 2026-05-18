# Hardening de la capa de auditoría (EMR)

Documento técnico post-revisión: riesgos, mitigaciones, limitaciones y roadmap sin implementaciones adicionales (no Celery/Kafka/event sourcing).

---

## 1. Riesgos identificados y mitigación

### 1.1 Consistencia transaccional / rollback

**Riesgo:** Insertar `AuditEvent` dentro de una transacción que luego hace rollback deja registros huérfanos o eventos contradictorios (“se audita el éxito” pero el trabajo clínico no quedó).

**Mitigación:** `auditoria.audit_service.log_event` programa la inserción con `transaction.on_commit()` cuando existe un bloque `atomic()` activo. Si la transacción revierte (incluso antes del commit estable), los callbacks registrados por `on_commit` **no se ejecutan** y **no debe persistirse** auditoría para esa operación.

**Sin `atomic()` en el call stack:** la inserción es **inmediata** (p. ej. scripts de comando, tests directos sobre `log_event`). Debe tratarse igual que antes: menor acoplamiento transaccional, asumido para casos fuera del flujo web.

### 1.2 Recursión y “auditar la auditoría”

**Riesgo:** Crear una fila sobre `AuditEvent` que disparara otra fila indefinida.

**Mitigación:** lista negra `_BLACKLIST_META_LABEL_LOWER` centrada en `auditoria.auditevent` + guardas en `_entity_blocked()`.

**Signals / serializers:** no hay señales global auditando modelos aleatorios; la integración es explícita en viewsets/services. Mantener ese patrón evita lazos ocultos en `save()` de serializers.

### 1.3 Snapshots grandes o sensibles (`safe_model_snapshot`)

**Riesgo:** Persistir payloads enormes en JSONField, blobs o rutas locales no deseadas; profundidad excesiva en campos tipo JSON nativo.

**Mitigación aplicada:**

- `FileField` / `ImageField`: marcador textual (`<file:nombre>` o equivalente corto); no contenido binario.
- `BinaryField`: marcador `<binary>` sin bytes.
- Strings largos: truncamiento en nivel hoja dentro del serializer.
- Tamaño total aprox.: si después de construir sigue sobrepasando el límite, se guarda snapshot mínimo con `__snapshot_error__` o se lanza `SnapshotTooLarge` en casos extremos.

**Campos que no deben considerarse persistencia exhaustiva:**

- Contraseñas, hashes, contenido raw de archivo, PHI en documentos externos (el snapshot es **no clínico** y orientado a campo local del modelo).

### 1.4 Metadatos y secretos (sanitizer)

**Riesgo:** Metadatos o estados antes/después llevan inadvertidamente `Authorization`, JWT, cookies, etc.

**Mitigación:** `auditoria.sanitizer.sanitize_dict_keys` redacta por **nombre de clave heurístico** (patrón tipo password/token/csrf/jwt/autorización/cookies…). **`enforce_max_json_payload`** acota tamaño tras sanitizar.

**Limitación:** no es DLP; no inspecciona valores que no están identificados por claves típicas. Valores grandes en texto libre (p. ej. “Bearer …” dentro de una nota titulada `obs`) pueden escaparse; mitigación operativa por permisos y UI.

### 1.5 Append-only efectivo en ORM Python

**Garantizado (ORM):**

- `AuditEvent.save()` bloquea actualizaciones (excepto alta).
- `AuditEvent.delete()` de instancia levanta `ValidationError`.
- `AuditEvent.objects.update()` y `.delete()` de queryset están sobreescritos para fallar (**`AuditEventQuerySet`**).

**Excepción conocida:**

- Django **`bulk_update()`** ejecuta `UPDATE` SQL sin invocar `save()` ni el `QuerySet` custom; **permite cambiar campos**. Mitigaciones futuras típicas: **REVOKE UPDATE** sobre la tabla al rol aplicación, políticas Postgres, o trígger `BEFORE UPDATE` que aborte. No implementado en este entregable (documentado a propósito).

**Borrado masivo rápido:** `QuerySet.delete()` puede en algunos escenarios usar “fast delete” SQL y **saltar** señales y APIs de modelo; la mitigación definitiva es **privilegio de BD** (revocación de `DELETE`). El intento aquí cubre el camino habitual del ORM vía queryset.

### 1.6 Performance (solo observación — sin optimización prematura)

**Coste base por llamada:**

- Una fila nueva en tabla `auditoria_auditevent`.
- Dos snapshots JSON opcionales (before/after) + serialización y sanitización.
- Contexto de request (contextvars).

**Consultas:** no se añadieron `select_related/prefetch` masivos dentro de auditoría para entidades vistas; snapshots usan valores escalares vía `_id` donde aplica sin recorrer colecciones M2M.

**Endpoints más impactados (por volumen de updates + logging):**

- Alta frecuencia de `PATCH`/acciones sobre turnos/atenciones/solicitudes/exámen cuando se registra `log_update`/`log_event` después de cada acción.

**Riesgos futuros:** sin retención, la tabla puede crecer sin techo (ver §3).

---

## 2. Índices PostgreSQL actual

Índices en modelo correspondientes al patrón de filtro del API de lectura (`entity_type` + `entity_id`, `request_id`, `actor`, `action`). Se evaluó índice compuesto con `timestamp`; con el patrón actual de filtros igualitarios prefijados puede ser útil revisar estadísticas antes de duplicar con `(entity_type, entity_id, timestamp)` para evitar escrituras duplicativas redundantes entre índices similares. **Sin migración nueva** en este ciclo donde el beneficio no estaba aclarado frente al índice existente sobre `(entity_type, entity_id)`.

---

## 3. Estimación de crecimiento y riesgos de almacenamiento (solo documentación)

**Orden de magnitud típico (orden de idea, depende del despliegue):**

| Supuesto conservador          | Ejemplo                                           |
|-----------------------------|---------------------------------------------------|
| Eventos / día por instalación modesta | 10³–10⁵ (consultas muy activas más arriba)           |
| Tamaño medio / evento JSON  | décenas de KiB máximo después de sanitizar/cap    |

Sin purga, volumen disco ~ lineal en el tiempo. **Sin implementar:**

- Particionado por rango temporal en PostgreSQL (`timestamp`).
- Tabla de archivo / cold storage compactada.
- Políticas de **retención legal** definidas junto cumplimiento (no sustituye asesoría jurídica).

**Riesgo legal/regulatorio:** el sistema **no garantiza por sí mismo** uso lícito de datos clínicos almacenados en auditoría; responsabilidades de DPIA/consentimiento/ROL permanecen nivel organización — la capa evita fugas triviales pero no clasifica HIPAA/GDPR automáticamente.

---

## 4. Fixes aplicados en código (referencia rápida)

- `transaction.on_commit` cuando `in_atomic_block` en `audit_service.log_event`.
- Blacklist para `AuditEvent` como entidad auditada.
- Sanitización y límite de tamaño sobre `before_state`, `after_state`, `metadata`.
- Endurecer `safe_model_snapshot` (archivos/binarios/strings largos, fallbacks de tamaño).
- `AuditEventQuerySet` que bloquea `update/delete` típicos.
- Tests específicos: rollback, blacklist, sanitización/truncamiento, append-only donde el ORM aplica; `bulk_update` documentado como bypass.

---

## 5. Roadmap sugerido (no implementado)

1. Privilegio de BD: `REVOKE UPDATE, DELETE` sobre `auditoria_auditevent` para usuario de aplicación + `INSERT`, `SELECT` sólo donde haga falta.
2. Opcional: política Postgres / trigger `BEFORE UPDATE OR DELETE RETURNING VOID` rechazando mutaciones fuera del rol técnico de migraciones.
3. Particionamiento + job de archivo según período contractual.
4. Métricas (Prometheus/logs) cuenta eventos/minuto desde observabilidad infra — sin acoplar a colas locales.
