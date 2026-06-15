# PROD_CHECKLIST — Despliegue inicial SYNESIS EMR/LIMS

**Fase:** PROD-1 / PROD-1-A / PROD-2-A / **PROD-2-B CERRADO** / **PROD-3 CERRADO** / **PROD-4 CERRADO** / **PROD-4-A CERRADO** / **PROD-4-B CERRADO** / **PROD-5 CERRADO** / **PROD-5-A CERRADO** / **PROD-6** (jun 2026)
**Alcance:** checklist operativo; no sustituye auditoría de seguridad ni despliegue completo.

---

## Antes del primer despliegue

### Variables de entorno obligatorias (`DEBUG=False`)

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` — generada con `get_random_secret_key()` o gestor de secretos (≥50 chars, ≥12 únicos, ≥3 clases de caracteres; **PROD-1-A** rechaza placeholders y baja entropía)
- [ ] No usar valores de `.env.production.example` como clave real
- [ ] `DJANGO_ALLOWED_HOSTS` — hosts explícitos (sin `*`)
- [ ] `DJANGO_CORS_ALLOWED_ORIGINS` — orígenes HTTPS del frontend
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` — mismos orígenes que consumen la API con cookies
- [ ] `DB_*` o equivalente — credenciales de Postgres de producción

### HTTPS y cookies

- [ ] `DJANGO_SECURE_SSL_REDIRECT=True` (si TLS en app o proxy)
- [ ] `DJANGO_SESSION_COOKIE_SECURE=True`
- [ ] `DJANGO_CSRF_COOKIE_SECURE=True`
- [ ] `DJANGO_USE_PROXY_SSL_HEADER=True` si TLS termina en reverse proxy
- [ ] HSTS (`DJANGO_SECURE_HSTS_SECONDS`) solo tras validar HTTPS end-to-end

### Django / DRF

- [ ] `python manage.py check --deploy` (revisar warnings)
- [ ] Browsable API **deshabilitada** con `DEBUG=False` (solo JSONRenderer)
- [ ] `/media/` **no** servido por Django (`synesis/urls.py` solo monta media si `DEBUG=True`)
- [ ] Archivos clínicos solo vía endpoints protegidos (`download/`, `informe-pdf/`, etc.)

### Base de datos

- [ ] Migraciones aplicadas en job controlado (no `RUN_MIGRATIONS=true` ad hoc en prod)
- [ ] Backups automáticos configurados (**pendiente** política formal PROD-2+)
- [ ] Restore probado (**pendiente**)

### Logging y PHI

- [ ] Nivel INFO/WARNING en producción; sin loguear payloads clínicos
- [ ] Revisar que apps no impriman `valor_obtenido`, DNI, `codigo_barra` en logs
- [ ] Auditoría `AuditEvent` append-only activa

### Frontend

- [ ] `REACT_APP_API_URL` apunta al API de producción
- [ ] Build estático servido por CDN/nginx (no `npm start` en prod)

### Docker (si aplica)

- [ ] Imagen sin credenciales dummy de `docker-compose.yml` dev
- [ ] `docker compose config` revisado
- [ ] **PROD-2-A:** `DJANGO_RUNTIME=gunicorn` en prod/staging (no `runserver`)
- [x] **PROD-2-B [CERRADO]:** tests ejecutables de `entrypoint.sh` pasan (`api/tests/test_prod_runtime_config.py` — 24 tests)
- [x] **PROD-2-B [CERRADO]:** healthcheck HTTP en `docker-compose.prod.example.yml` — `/api/health/`, `DJANGO_HEALTHCHECK_HOST`, headers `Host` / `X-Forwarded-Proto`
- [x] **PROD-3 [CERRADO]:** plantilla `deploy/nginx/nginx.prod.example.conf` — proxy, headers, `/media/` bloqueado
- [x] **PROD-3 [CERRADO]:** servicio `nginx` en compose; Gunicorn solo red interna
- [x] **PROD-3 [CERRADO]:** `nginx -t` con Docker OK (`nginx:1.27-alpine`, `--add-host backend:127.0.0.1`)
- [x] **PROD-3 [CERRADO]:** `depends_on`: nginx → backend healthy (no al revés)
- [ ] `docker-compose.prod.example.yml` revisado con variables `${...}` (sin secretos en repo)
- [x] **PROD-4 [CERRADO]:** `/media/` bloqueado Nginx + Django prod; descargas vía API autenticada
- [x] **PROD-4 [CERRADO]:** compose prod sin volumen media en Nginx; volumen backend opcional documentado
- [ ] Volúmenes persistentes para Postgres y media/storage privado (montar en staging)

---

## Comandos de verificación pre-release

```bash
./emr_env/bin/python manage.py check
./emr_env/bin/python manage.py makemigrations --check --dry-run
./emr_env/bin/pytest api/tests/test_prod_settings_security.py api/tests/test_prod_runtime_config.py -q --reuse-db
```

Validar compose con variables dummy (nunca secretos reales):

```bash
docker compose config
DJANGO_SECRET_KEY=dummy-secret \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,example.com \
DJANGO_HEALTHCHECK_HOST=localhost \
DJANGO_CORS_ALLOWED_ORIGINS=https://localhost \
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com \
DB_PASSWORD=dummy-password \
docker compose -f docker-compose.prod.example.yml config
```

Con `DJANGO_DEBUG=False` y env de producción (staging):

```bash
DJANGO_DEBUG=False DJANGO_SECRET_KEY=... DJANGO_ALLOWED_HOSTS=... \
  DJANGO_CORS_ALLOWED_ORIGINS=... DJANGO_CSRF_TRUSTED_ORIGINS=... \
  ./emr_env/bin/python manage.py check --deploy
```

---

## Pendiente post-PROD-1

- Política de retención y borrado de auditoría legal
- WAF / rate limiting
- Rotación de secretos
- Monitoreo y alertas (Sentry/Datadog)
- ~~Job de backups/restore documentado~~ — **PROD-5:** `deploy/backup/*.example.sh` + README
- ~~`gunicorn` + workers~~ — **mitigado (PROD-2-A):** `entrypoint.sh` soporta `DJANGO_RUNTIME=gunicorn`; dev sigue con `runserver`
- ~~Healthcheck HTTP Gunicorn~~ — **mitigado (PROD-2-B):** `GET /api/health/` con `DJANGO_HEALTHCHECK_HOST`, header `Host` y `X-Forwarded-Proto: https`
- ~~Nginx / reverse proxy en compose~~ — **mitigado (PROD-3 CERRADO):** plantilla + servicio nginx; `nginx -t` validado
- Storage object privado (S3/MinIO) para media clínica
- npm audit / dependabot frontend (no ejecutar `npm audit fix` automático en PROD-1)

---

## PROD-2-B — CERRADO (jun 2026)

Verificación ejecutable runtime Gunicorn + healthcheck productivo. **Sin cambios funcionales EMR/LIMS.**

| Validación | Resultado documentado |
|------------|----------------------|
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| `test_prod_runtime_config.py` | 24 passed |
| Regresión seguridad/runtime/LIMS | 48 passed |
| `docker compose config` | OK |
| Compose prod example (vars dummy) | OK |

**Mitigado:** entrypoint ejecutable; healthcheck con `DJANGO_HEALTHCHECK_HOST` compatible con `ALLOWED_HOSTS` y `SECURE_SSL_REDIRECT`.

**Pendiente fuera de alcance:** storage privado, backups/restore, WAF/rate limiting, monitoreo externo, rotación de secretos. Ver `PROD_RUNTIME.md`.

---

## PROD-3 — CERRADO (jun 2026)

Reverse proxy Nginx + headers TLS externo. **Sin cambios funcionales EMR/LIMS.**

| Validación | Resultado documentado |
|------------|----------------------|
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| `test_prod_runtime_config.py` | 39 passed |
| Regresión seguridad/runtime/LIMS | 63 passed |
| `docker compose config` | OK |
| Compose prod example (vars dummy) | OK |
| `nginx -t` (Docker) | OK |

**Mitigado:** Nginx reverse proxy; headers proxy; `/media/` bloqueado; `X-Forwarded-Proto` preserva LB externo; healthcheck PROD-2-B conservado.

**Pendiente fuera de alcance:** certificados TLS reales/ACME, object storage S3/MinIO real, backups/restore, WAF/rate limiting, monitoreo externo, rotación de secretos.

---

## PROD-4 — CERRADO (jun 2026)

Storage privado para media clínica y archivos sensibles. **Sin cambios funcionales EMR/LIMS.**

### Archivos del commit (11)

Incluye **10 modified** + **`deploy/nginx/nginx.prod.example.conf` (untracked)**. Ver listado completo y comando `git add` en `PROD_RUNTIME.md`. No usar `git add ..`.

| Validación | Resultado documentado |
|------------|----------------------|
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| `test_prod_runtime_config.py` | **49 passed** |
| `archivos_medicos/tests/` | **33 passed** |
| Regresión seguridad/runtime/LIMS | **73 passed** |
| `docker compose config` | OK |
| Compose prod example (vars dummy) | OK |
| `nginx -t` (Docker) | OK |
| `git diff --check` | OK |

**Mitigado:** Nginx y Django prod no sirven `/media/`; archivos clínicos principales por endpoints autenticados; política documentada; sin credenciales cloud en repo; plantilla Nginx trackeable vía staging explícito.

**Pendiente fuera de alcance PROD-4:** object storage real, backups/restore, WAF, monitoreo externo.

---

## PROD-4-A — CERRADO (jun 2026)

Descarga segura de adjuntos clínicos en registros de procedimiento y quirúrgicos. **Sin cambios en modelos, migraciones, permisos EMR/LIMS, reglas clínicas, estados ni frontend.**

### Checklist de cierre

- [x] `GET /api/registros-procedimientos/{id}/download-adjunto-resultado/` — autenticado; `get_object()`; `FileResponse`; 404 sin archivo
- [x] `GET /api/registros-quirurgicos/{id}/download-consentimiento-informado/` — idem
- [x] Serializers sin `/media/` en lectura; `*_download_url` y `*_nombre` expuestos
- [x] `adjunto_resultado` / `consentimiento_informado` write-only para upload
- [x] Anónimo bloqueado; usuario ajeno bloqueado; autorizado descarga según visibilidad actual
- [x] Tests PROD-4-A: **15 passed**
- [x] Regresión mínima: **106 passed**
- [x] `manage.py check` OK; `makemigrations --check --dry-run` sin cambios
- [x] Compose dev/prod OK; `nginx -t` OK; `git diff --check` OK
- [x] `/media/` sigue bloqueado; Nginx sin cambios en esta fase

### Archivos del commit PROD-4-A (10)

Ver listado y comando `git add` en `PROD_RUNTIME.md` (sección Cierre PROD-4-A). **No mezclar** con archivos PROD-4 (`.env.production.example`, `docker-compose.prod.example.yml`, `test_prod_runtime_config.py`, etc.).

| Validación | Resultado |
|------------|-----------|
| `test_registro_adjuntos_download_prod4a.py` | **15 passed** |
| Regresión mínima | **106 passed** |
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| Compose + `nginx -t` | OK |

**Pendiente fuera de alcance PROD-4-A:** S3/MinIO; TLS/ACME; WAF; backups; monitoreo externo.

---

## PROD-4-B — CERRADO (jun 2026)

Auditoría de descarga exitosa para adjuntos turnos. **Sin cambios en modelos, migraciones, permisos EMR/LIMS, frontend ni Nginx.**

### Checklist de cierre

- [x] Descarga `adjunto_resultado` audita `registro_procedimiento_adjunto_download`
- [x] Descarga `consentimiento_informado` audita `registro_quirurgico_consentimiento_download`
- [x] `log_event` con `module=turnos`, `after=None`; metadata: `field`, `endpoint`, `view`
- [x] Sin path absoluto, `/media/`, filename ni contenido en auditoría
- [x] No autorizado / sin archivo no genera evento de descarga exitosa
- [x] Tests `test_registro_adjuntos_download_audit_prod4b.py`

### Archivos del commit PROD-4-B (staging explícito, sin `git add ..`)

| Archivo | Notas |
|---------|-------|
| `api/views.py` | `_audit_turnos_registro_download()`; callback en descargas (delta sobre PROD-4-A si commit separado) |
| `api/tests/test_registro_adjuntos_download_audit_prod4b.py` | Suite auditoría — **6 passed** |
| `docs_synesis/DOC_*.md`, `PROD_*.md` | Cierre documental |

**No mezclar en staging PROD-4-B:** `.env.production.example`, `docker-compose.prod.example.yml`, `api/tests/test_prod_runtime_config.py`, `archivos_medicos/tests/test_api_security_c62.py`, `deploy/`, `api/serializers.py` / `test_registro_adjuntos_download_prod4a.py` (alcance PROD-4-A si ya commiteados).

| Validación | Resultado |
|------------|-----------|
| `test_registro_adjuntos_download_audit_prod4b.py` | **6 passed** |
| `test_registro_adjuntos_download_prod4a.py` | **15 passed** |
| Regresión mínima (+ PROD-4-A) | **121 passed** |
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| Compose dev/prod + `nginx -t` | OK |
| `git diff --check` | OK |

**Observación técnica:** se usa `action='UPDATE'` por compatibilidad con Documento/ArchivoMedico/LIMS PDF; no se introduce acción global `DOWNLOAD` en esta fase.

**Pendiente fuera de alcance PROD-4-B:** S3/MinIO; TLS/ACME; WAF; monitoreo externo.

---

## PROD-5 — CERRADO (jun 2026)

Plantillas operativas PostgreSQL + media. **Sin restore real ejecutado; sin modelos, permisos, frontend ni cron en compose.**

### Checklist de cierre

- [x] Scripts `deploy/backup/*.example.sh` + README
- [x] Restore: `CONFIRM_RESTORE=true`, `RESTORE_TARGET_DB`, `BACKUP_FILE`
- [x] Checksums; `.gitignore` artefactos
- [x] Tests `test_prod_backup_config.py` — **31 passed**
- [x] Runtime + PROD-5 — **80 passed**; regresión — **127 passed**
- [x] `bash -n`, compose, `nginx -t`, checks Django OK
- [x] `backup_pendrive.sql` ignorado/no trackeado (mover fuera del repo si sensible)

| Validación | Resultado |
|------------|-----------|
| `test_prod_backup_config.py` | **31 passed** |
| Runtime + PROD-5 | **80 passed** |
| Regresión mínima | **127 passed** |

**Staging:** ver `PROD_RUNTIME.md` sección PROD-5 CERRADO.

**Operador pendiente:** cifrado offsite, retención, scheduling externo, **ejecución del drill en infra staging real** (`RESTORE_DRILL_STAGING.md`).

---

## PROD-5-A — Restore drill staging (jun 2026)

- [x] `deploy/backup/RESTORE_DRILL_STAGING.md`
- [x] `deploy/backup/verify_restore.example.sh`
- [x] `api/tests/test_prod_restore_drill_config.py`
- [ ] Operador: ejecutar drill en staging aislado (fuera del repo)

---

## PROD-6 — Readiness productivo controlado / Smoke E2E (jun 2026)

Piloto técnico backend/API; **no** producción clínica abierta. Ver **`PROD_READINESS_SMOKE.md`**.

- [ ] Documentación readiness + GO/NO-GO + runbook reversión
- [ ] Matriz roles mínima; solo datos sintéticos en smoke inicial
- [ ] Script `deploy/smoke/prod_readiness_smoke.example.sh` (parametrizado; sin secretos)
- [ ] Tests `test_prod_readiness_smoke.py` + regresión mínima OK
- [ ] Health, auth, media privada, descargas+auditoría (tests existentes)
- [ ] Backup/restore drill como checklist; **sin restore real** en smoke inicial
- [ ] Frontend no versionado — validar UI en repo/despliegue real antes de go-live clínico

---

## Referencias

- `docs_synesis/DOC_BACKEND.md` — configuración PROD-1 / runtime / Nginx
- `docs_synesis/DOC_PERMISOS_AUDITORIA.md` — permisos y auditoría
- `docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md` — riesgos residuales
- `.env.production.example` — plantilla de variables
