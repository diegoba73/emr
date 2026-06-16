# PROD-9 — Observabilidad mínima (piloto productivo técnico controlado)

**Fase:** PROD-9 — plan operativo de observabilidad mínima  
**Estado:** documentación + checks no destructivos  
**Fecha:** junio 2026

---

## Objetivo

Definir una **base mínima de observabilidad** para operar SYNESIS EMR/LIMS en un **piloto productivo técnico controlado** (staging/pilot), integrando fases PROD-1 a PROD-8.

**PROD-9 no habilita producción clínica abierta.** Documenta dónde observar, qué verificar y cómo responder ante incidentes — no sustituye SRE 24/7 ni monitoreo externo completo (Datadog/Sentry/Prometheus) si el operador aún no los despliega.

---

## Alcance

| Incluye | No incluye |
|---------|------------|
| Fuentes de logs (backend/Gunicorn, Nginx, PostgreSQL) | Producción clínica abierta |
| Detección documentada de errores 4xx/5xx | PHI en logs, evidencia o repo |
| Healthcheck externo `GET /api/health/` | Modificar modelos, permisos, endpoints |
| Monitoreo básico contenedores, DB, disco | Restore destructivo |
| Backups programados (definición operativa) | Dependencias nuevas en backend |
| Procedimientos de incidente | Observabilidad UX/frontend en este repo |
| GO/NO-GO operativo y evidencia sanitizada | Tokens, passwords, dumps en git |

---

## Fuera de alcance explícito

- **Producción clínica abierta** a usuarios finales sin control.
- Implementación obligatoria de Sentry/Datadog/Prometheus (recomendado como mejora operador).
- Observabilidad de navegador, errores JS, performance UI (frontend en despliegue separado).
- Cambios funcionales EMR/LIMS, auditoría, Nginx productivo ejecutable.

---

## Estado previo requerido

Antes de aplicar PROD-9 en un piloto:

- [ ] PROD-8 checklist pre-piloto revisado (`PROD_PREPILOT_CHECKLIST.md`).
- [ ] PROD-7 restore drill GO técnico o excepción formal documentada.
- [ ] Stack prod example: Gunicorn + Nginx + Postgres (`docker-compose.prod.example.yml`).
- [ ] Responsable operativo nominal definido **fuera del repo**.
- [ ] `DEBUG=False`, secretos fuera del repo, `/media/` no público.

---

## Fuentes de observabilidad

| Componente | Dónde consultar (genérico) |
|------------|---------------------------|
| Backend / Gunicorn | `docker logs <backend_container>` o agregador del orquestador |
| Nginx / reverse proxy | `docker logs <nginx_container>`; access log con códigos HTTP |
| PostgreSQL | `docker logs <db_container>`; `pg_isready` dentro del contenedor |
| Healthcheck API | `GET /api/health/` vía proxy o interno |
| Compose health | `docker inspect --format '{{.State.Health.Status}}' <container>` |
| Disco | `df -h` en host; `docker system df` (volumen DB, backups, media, logs) |
| Backups | Directorio fuera del repo definido por operador; logs del scheduler |
| Auditoría app | Tabla `auditoria_auditevent` — solo conteos agregados en evidencia |

Script de ejemplo no destructivo: `deploy/observability/check_observability.example.sh`.

---

## Logs backend / Gunicorn

### Qué observar

- Arranque Gunicorn (`DJANGO_RUNTIME=gunicorn` en `entrypoint.sh`).
- Errores WSGI, timeouts (`GUNICORN_TIMEOUT`), workers caídos.
- `DisallowedHost`, errores de configuración Django.
- Migraciones fallidas si `RUN_MIGRATIONS=true`.

### Comandos orientativos (no destructivos)

```bash
docker logs --tail 200 <backend_container>
docker inspect --format '{{.State.Status}} {{.RestartCount}}' <backend_container>
```

### Reglas

- **No** loguear payloads clínicos, DNI, `valor_obtenido`, `codigo_barra`.
- **No** imprimir `SECRET_KEY`, `DATABASE_URL` completa ni tokens.
- Acceso a logs restringido a roles operativos autorizados.

---

## Logs Nginx / proxy

### Qué observar

- Códigos HTTP en access log: **4xx** (cliente/auth) y **5xx** (upstream/backend).
- Picos de `502`/`503`/`504` → backend o DB indisponible.
- Intentos a `/media/` → deben ser **404/403**, nunca `200` con contenido clínico.
- Upstream `backend:8000` unreachable.

### Comandos orientativos

```bash
docker logs --tail 200 <nginx_container>
```

### Umbrales sugeridos (operador)

| Señal | Acción |
|-------|--------|
| 5xx sostenido > N min | Incidente backend/DB |
| `/media/` → 200 | **Incidente seguridad** — posible exposición |
| 401/403 en APIs protegidas anónimas | Comportamiento esperado |

---

## Logs PostgreSQL

### Qué observar

- Contenedor `db` healthy (`pg_isready`).
- Errores de conexión, disco lleno, checkpoint, recovery.
- Conexiones agotadas.

### Comandos orientativos (sin PHI)

```bash
docker exec <db_container> pg_isready -U postgres
docker logs --tail 100 <db_container>
```

Conteos agregados permitidos en evidencia (sin listar filas):

```sql
SELECT COUNT(*) FROM pacientes_paciente;
SELECT pg_database_size(current_database());
```

---

## Healthcheck externo

| Endpoint | Auth | Criterio piloto |
|----------|------|-----------------|
| `GET /api/health/` | No | `200` |
| `GET /media/` | No | ≠ `200` |
| `GET /api/pacientes/` | No (anónimo) | `401` o `403`, **no** `200` |

Probe interno compose (PROD-2-B): healthcheck en contenedor `backend` a `127.0.0.1:8000/api/health/` con `DJANGO_HEALTHCHECK_HOST` y `X-Forwarded-Proto: https`.

Smoke remoto: `deploy/smoke/prod_readiness_smoke.example.sh` (`BASE_URL` sin credenciales en repo).

---

## Monitoreo de contenedores

Verificar periódicamente (ventana piloto):

| Check | Comando / señal |
|-------|-----------------|
| Estado running | `docker ps --filter name=<prefix>` |
| Health status | `healthy` / `unhealthy` / `starting` |
| Restart count | `docker inspect --format '{{.RestartCount}}'` |
| Dependencias compose | `nginx` → `backend` healthy; `backend` → `db` healthy |

Alerta si `RestartCount` crece sin explicación o health permanece `unhealthy` > umbral operativo.

---

## Monitoreo de base de datos

| Check | Descripción |
|-------|-------------|
| Contenedor activo | `pg_isready` OK |
| Conexión desde backend | Healthcheck backend OK implica conectividad básica |
| Tamaño aproximado | `pg_database_size` — registrar solo entero en evidencia |
| Conteos agregados | `COUNT(*)` tablas críticas — sin PHI |
| Migraciones | Job controlado; no `RUN_MIGRATIONS=true` ad hoc en prod |

**No** ejecutar `DROP`, `TRUNCATE` ni restore sobre DB activa desde checks de observabilidad.

---

## Monitoreo de espacio en disco

Monitorear en host o nodos del orquestador:

| Área | Riesgo si lleno |
|------|-----------------|
| Volumen PostgreSQL | DB caída / corrupción |
| `MEDIA_ROOT` / volumen media backend | Uploads fallan; descargas 404 |
| Directorio backups (fuera repo) | Backups fallan |
| Logs Docker / journal | Pérdida de trazabilidad; servicios inestables |

```bash
df -h
docker system df
```

Umbral sugerido: alertar operador antes de 85–90 % en volúmenes críticos.

---

## Backups programados

- Política definida **fuera del repo**: frecuencia, retención, responsable.
- Scripts: `deploy/backup/backup_postgres.example.sh`, `backup_media.example.sh`.
- Verificar existencia de artefactos recientes y checksums `.sha256` — **sin abrir dumps**.
- Fallo de backup → incidente operativo; no commitear artefactos.

---

## Restore drill PROD-7 (antecedente)

PROD-9 asume que la recuperabilidad fue validada en staging controlado (PROD-7 GO técnico) o excepción formal.

- Procedimiento: `deploy/backup/RESTORE_DRILL_STAGING.md`
- Verificación: `verify_restore.example.sh`
- Evidencia sanitizada fuera del repo

Observabilidad de backups **no** reemplaza drill de restore.

---

## Smoke operativo mínimo

1. `deploy/observability/check_observability.example.sh` — checks locales no destructivos.
2. `deploy/smoke/prod_readiness_smoke.example.sh` — smoke remoto con `BASE_URL`.
3. Login sintético opcional: `SMOKE_USERNAME` / `SMOKE_PASSWORD` vía entorno — **no documentar en repo**.

Endpoints documentados (sin modificar):

- `GET /api/health/`
- `GET /media/`
- `GET /api/pacientes/` (anónimo bloqueado)
- `POST /api/auth/login/` (solo usuario sintético autorizado)
- `GET /api/auth/current-user/` (si smoke autenticado)

---

## Incidentes y respuesta

**Responsable operativo / incidentes:** definido por operador fuera del repo (nombre/rol interno, contacto escalamiento).

### Backend caído

1. Confirmar healthcheck `unhealthy` o 5xx en Nginx.
2. Revisar logs Gunicorn (`docker logs backend`).
3. Verificar DB reachable (`pg_isready`).
4. Reiniciar contenedor backend si causa transitoria (documentar en evidencia).
5. Si persiste: rollback imagen/tag anterior (ver `PROD_PREPILOT_CHECKLIST.md` rollback).
6. Registrar incidente sanitizado fuera del repo.

### DB caída

1. `pg_isready` falla; backend 5xx.
2. Revisar logs PostgreSQL y disco del volumen.
3. **No** restaurar backup sobre DB activa sin ventana formal.
4. Escalar a DBA/operador infra.
5. Tras recuperación: `manage.py check` en staging; conteos agregados.

### Nginx / proxy caído

1. API no alcanzable externamente; backend puede estar healthy internamente.
2. Revisar logs Nginx, configuración, upstream.
3. `nginx -t` en plantilla o contenedor.
4. Reiniciar servicio nginx; verificar `GET /api/health/` externo.

### Media privada no disponible

1. Uploads o descargas autenticadas fallan (404/500).
2. Verificar volumen `MEDIA_ROOT` montado en backend (no en Nginx).
3. Verificar espacio en disco del volumen media.
4. **No** exponer `/media/` públicamente como workaround.
5. Restore media solo en directorio temporal (PROD-7), nunca sobre activo sin autorización.

### Disco lleno

1. Alerta `df` / `docker system df`.
2. Rotar o archivar logs según política.
3. Verificar backups no llenan partición compartida.
4. Expandir volumen o limpiar según política — **sin** borrar DB activa ni backups únicos sin confirmación.

### Backups fallando

1. Revisar logs del job scheduler (cron/systemd/K8s CronJob).
2. Verificar credenciales vía gestor de secretos (no imprimir).
3. Verificar espacio en `BACKUP_DIR`.
4. Ejecutar backup manual en ventana controlada si aplica.

### Errores 5xx sostenidos

1. Correlacionar Nginx access log con backend logs.
2. Identificar endpoint afectado (sin imprimir payloads clínicos).
3. Verificar DB, disco, workers Gunicorn.
4. GO/NO-GO piloto según duración e impacto.

### Sospecha de exposición de PHI

1. **Detener** tráfico al entorno si riesgo confirmado (`/media/` público, API anónima 200 en datos clínicos).
2. Preservar logs **sin** copiar PHI al repo.
3. Notificar responsable seguridad institucional.
4. Documentar incidente sanitizado; activar rollback.
5. **No** habilitar producción clínica hasta cierre formal.

### Auditoría crítica (observación sin PHI)

- Descargas protegidas PROD-4-B: verificar que eventos `registro_*_download` se generan en descargas exitosas (conteo agregado).
- LIMS: auditoría de transiciones según fases cerradas.
- Request ID: registrar si el stack lo provee; no obligatorio en PROD-9 documental.

---

## Evidencia permitida

Fuera del repo, sanitizada:

- Fecha/hora, entorno (staging/pilot), commit HEAD.
- Códigos HTTP agregados, health status, restart counts.
- Porcentaje disco, tamaño DB (entero).
- Resultado scripts `check_observability` / smoke.
- GO/NO-GO operativo.
- Identificador interno del operador.

---

## Evidencia prohibida

- PHI, DNI, nombres de pacientes, resultados clínicos.
- Tokens, passwords, cookies, `SECRET_KEY`.
- Dumps, backups, logs completos con datos sensibles.
- Paths internos que revelen archivos clínicos.
- Capturas con datos de pacientes.

---

## Criterios GO / NO-GO operativos

### GO (observabilidad mínima lista para piloto técnico)

- Fuentes de logs identificadas y accesibles para operador autorizado.
- Healthcheck externo `GET /api/health/` → 200 en ventana de prueba.
- `/media/` no público; APIs protegidas anónimas ≠ 200.
- Procedimientos de incidente documentados y responsable asignado.
- Monitoreo contenedores/DB/disco definido (manual o script ejemplo).
- Backups programados definidos; PROD-7 referenciado.
- Evidencia sanitizada archivada fuera del repo.
- **Producción clínica abierta: FUERA DE ALCANCE.**

### NO-GO

- Sin responsable operativo.
- Healthcheck falla sostenidamente.
- `/media/` público o APIs clínicas anónimas en 200.
- Backups sin política ni verificación.
- PHI o secretos en evidencia/commits.
- Intento de piloto clínico abierto.

---

## Frontend

**Este repositorio backend no contiene la SPA React canónica en la raíz.** Submódulo `frontend/` o despliegue separado requiere **observabilidad propia** (errores JS, performance, sesiones).

PROD-9 cubre backend/infra; **no** valida UX ni telemetría de navegador.

---

## Checklist final (operador)

```
[ ] Logs backend/Gunicorn accesibles
[ ] Logs Nginx/proxy accesibles
[ ] Logs PostgreSQL accesibles
[ ] Procedimiento 4xx/5xx definido
[ ] GET /api/health/ externo OK
[ ] GET /media/ no público
[ ] GET /api/pacientes/ anónimo 401/403
[ ] Contenedores: estado + health + restart count revisados
[ ] DB: pg_isready + tamaño agregado documentado
[ ] Disco: DB, media, backups, logs monitoreados
[ ] Backups programados definidos fuera del repo
[ ] PROD-7 restore drill referenciado
[ ] Responsable operativo definido fuera del repo
[ ] Procedimientos incidente revisados
[ ] check_observability.example.sh ejecutado (si aplica)
[ ] Smoke PROD-6 ejecutado
[ ] Evidencia sanitizada fuera del repo
[ ] GO/NO-GO registrado
[ ] Frontend: observabilidad separada si aplica UI
[ ] Producción clínica abierta: FUERA DE ALCANCE
```

---

## Referencias

| Documento | Contenido |
|-----------|-----------|
| `PROD_PREPILOT_CHECKLIST.md` | Pre-piloto PROD-8 |
| `PROD_READINESS_SMOKE.md` | Smoke PROD-6 |
| `PROD_RUNTIME.md` | Gunicorn, Nginx, healthcheck |
| `deploy/observability/README.md` | Scripts observabilidad |
| `deploy/backup/README.md` | Backups |
| `DOC_RIESGOS_DEUDA_TECNICA.md` | Riesgos residuales |

---

## Siguiente fase recomendada

**PROD-10 — Piloto técnico controlado ejecutado:** aplicar PROD-8 + PROD-9 en ventana real con evidencia operativa, o integrar monitoreo externo (Sentry/Datadog/Prometheus) según madurez del operador.
