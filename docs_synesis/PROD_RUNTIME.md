# PROD_RUNTIME — Runtime backend SYNESIS EMR/LIMS

**Fase:** PROD-2-A / PROD-2-B / **PROD-3** / **PROD-4** (jun 2026)
**Estado PROD-2-B:** **CERRADO** (7 jun 2026)
**Estado PROD-3:** **CERRADO** (7 jun 2026) — reverse proxy Nginx + headers TLS externo
**Estado PROD-4:** **CERRADO** (8 jun 2026) — media clínica privada; sin serving público `/media/`
**Estado PROD-4-A:** **CERRADO** (8 jun 2026) — descarga segura adjuntos procedimiento/quirúrgico vía API
**Estado PROD-4-B:** **CERRADO** (jun 2026) — auditoría de descarga adjuntos turnos
**Estado PROD-5:** **CERRADO** (jun 2026) — plantillas backup/restore PostgreSQL + media
**Estado PROD-5-A:** **IMPLEMENTADO** (jun 2026) — restore drill staging documentado + verificación no destructiva
**Estado PROD-8:** **IMPLEMENTADO** (jun 2026) — checklist pre-piloto productivo / GO-NO-GO documental
**Estado PROD-9:** **IMPLEMENTADO** (jun 2026) — observabilidad mínima documental + checks no destructivos
**Estado PROD-10:** **IMPLEMENTADO** (jun 2026) — runbook piloto técnico + plantilla evidencia + smoke
**Estado PROD-11:** **IMPLEMENTADO** (jun 2026) — revisión post-piloto + plantilla acciones correctivas
**Estado PROD-12:** **IMPLEMENTADO** (jun 2026) — autorización institucional y piloto datos reales mínimos (documental)
**Estado PROD-13:** **IMPLEMENTADO** (jun 2026) — hardening operativo sostenido (documental)
**Alcance:** runtime WSGI (dev vs prod), reverse proxy Nginx, política de media/uploads privados; sin S3/MinIO real ni certificados en repo.

---

## Cierre PROD-2-B (evidencia)

**Implementado y validado (sin impacto EMR/LIMS):**

| Entregable | Evidencia |
|------------|-----------|
| Tests ejecutables `entrypoint.sh` | `api/tests/test_prod_runtime_config.py` — stubs `nc`/`python`/`gunicorn`/`sleep`; sin Postgres ni servidor real |
| Runtime inválido | `exit 1`, mensaje claro, sin secretos en salida |
| Rama `runserver` (dev) | Invoca `manage.py runserver` con `BIND_ADDR` |
| Rama `gunicorn` (prod/staging) | Invoca `synesis.wsgi:application` con workers/timeout/bind |
| `RUN_MIGRATIONS` | `false` → no migra; `true` → intenta `migrate --noinput` (stub) |
| No exposición de secretos | `SECRET_KEY` dummy ausente en stdout/stderr |
| Healthcheck productivo | `GET /api/health/` interno; `DJANGO_HEALTHCHECK_HOST`; headers `Host` y `X-Forwarded-Proto: https` |
| Compose dev/prod | `docker-compose.yml` → `runserver`; `docker-compose.prod.example.yml` → `gunicorn` |

**Validación documentada (jun 2026):** `manage.py check` OK; `makemigrations --check --dry-run` sin cambios; **24 passed** en `test_prod_runtime_config.py`; **48 passed** regresión seguridad/runtime/LIMS; `docker compose config` OK; compose prod example OK con variables dummy.

**Fuera de alcance PROD-2-B (pendiente fases posteriores):** ~~Nginx/reverse proxy~~ (**PROD-3**), storage privado, backups/restore, WAF/rate limiting, monitoreo externo (Sentry/Datadog), rotación de secretos. Sin cambios en modelos, migraciones, permisos EMR/LIMS, reglas clínicas, estados, frontend ni endpoints funcionales.

**Nota:** `docker compose config` valida sintaxis; no garantiza respuesta `200` del healthcheck en runtime.

---

## Variable de control

| Variable | Valores | Uso |
|----------|---------|-----|
| `DJANGO_RUNTIME` | `runserver` \| `gunicorn` | Selecciona proceso en `entrypoint.sh` |

Opcionales (solo `gunicorn`):

| Variable | Default | Descripción |
|----------|---------|-------------|
| `GUNICORN_WORKERS` | `3` | Workers WSGI |
| `GUNICORN_TIMEOUT` | `120` | Timeout en segundos |
| `BIND_ADDR` | `0.0.0.0:8000` | Bind address |

---

## Desarrollo local

**`docker-compose.yml`** (stack dev):

```yaml
DJANGO_DEBUG: "true"
DJANGO_RUNTIME: "runserver"
```

Comando equivalente sin Docker:

```bash
python manage.py runserver 0.0.0.0:8000
```

---

## Producción / staging

**No usar `runserver` en producción.**

Plantillas:

- `.env.production.example` → `DJANGO_RUNTIME=gunicorn`
- `docker-compose.prod.example.yml` → `DJANGO_RUNTIME: "gunicorn"`

Arranque vía entrypoint:

```bash
gunicorn synesis.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

Validación local (sin servidor persistente):

```bash
./emr_env/bin/gunicorn --version
./emr_env/bin/gunicorn synesis.wsgi:application --check-config
```

### Healthcheck HTTP (PROD-2-B)

`docker-compose.prod.example.yml` incluye healthcheck sobre el endpoint existente `GET /api/health/` (no sensible, sin autenticación).

Usa Python (`urllib`) ya presente en la imagen `python:3.10-slim`; no se agregaron `curl` ni `wget`.

Comportamiento:

- El probe apunta a `http://127.0.0.1:8000/api/health/` **dentro del contenedor** (Gunicorn escucha en loopback interno).
- El header `Host` se toma de `DJANGO_HEALTHCHECK_HOST` (default `localhost` en compose).
- **`DJANGO_HEALTHCHECK_HOST` debe estar incluido en `DJANGO_ALLOWED_HOSTS`**, o Django responderá `400 DisallowedHost` y el contenedor quedará `unhealthy`.
- Con `DJANGO_SECURE_SSL_REDIRECT=True`, un GET HTTP plano recibiría redirección `301` a HTTPS. El healthcheck envía `X-Forwarded-Proto: https` para simular TLS terminado en proxy.
- Ese header solo evita la redirección si `DJANGO_USE_PROXY_SSL_HEADER=True` (activo en la plantilla prod); en ese caso Django usa `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` (`synesis/settings.py`).
- `docker compose config` valida **sintaxis** del compose; **no garantiza** que el healthcheck responda `200` en runtime (depende de ALLOWED_HOSTS, settings y Gunicorn levantado).

Variable en `.env.production.example`:

```bash
DJANGO_HEALTHCHECK_HOST=localhost
```

Asegurar que el valor figure en `DJANGO_ALLOWED_HOSTS` (p. ej. incluir `localhost` para healthcheck interno, o usar el FQDN público como host del probe).

El healthcheck verifica que Gunicorn responde; no sustituye monitoreo externo ni validación de Postgres.

---

## Reverse proxy Nginx (PROD-3 — CERRADO)

### Cierre PROD-3 (evidencia, jun 2026)

**Implementado y validado (sin impacto EMR/LIMS):**

| Entregable | Evidencia |
|------------|-----------|
| Plantilla Nginx | `deploy/nginx/nginx.prod.example.conf` |
| Reverse proxy | `nginx:80` → `backend:8000` (Gunicorn); backend sin `8000:8000` público |
| Headers proxy | `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` (`$proxy_x_forwarded_proto`) |
| LB externo | Map preserva `$http_x_forwarded_proto`; fallback `$scheme` |
| `/media/` | Bloqueado en Nginx (no PHI público) |
| Dotfiles | Bloqueados; `.well-known/` placeholder ACME |
| Healthcheck PROD-2-B | Intacto en contenedor `backend` |
| `depends_on` | `nginx` → `backend` healthy; `backend` → `db` healthy |
| `nginx -t` Docker | `syntax is ok` / `test is successful` |
| Tests | **39 passed** runtime; **63 passed** regresión seguridad/runtime/LIMS |
| Compose | dev OK; prod example OK (vars dummy) |

**Endpoint healthcheck:** `GET /api/health/` — no sensible; probe interno backend; Nginx lo proxya como cualquier ruta API.

**Fuera de alcance PROD-3:** certificados TLS reales, ACME, storage privado, backups/restore, WAF/rate limiting, monitoreo externo, rotación de secretos.

---

**Plantilla:** `deploy/nginx/nginx.prod.example.conf`

**Compose prod:** servicio `nginx` (`nginx:1.27-alpine`) expone puerto `80`; `backend` (Gunicorn) solo en red interna (`expose: 8000`).

### Arquitectura

```
Cliente → [TLS externo / LB] → Nginx:80 → backend:8000 (Gunicorn/Django)
```

- Gunicorn sigue seleccionado por `DJANGO_RUNTIME=gunicorn` en `entrypoint.sh`.
- TLS es responsabilidad del Nginx, balanceador cloud o infraestructura externa; **no hay certificados reales en el repo**.
- Healthcheck PROD-2-B permanece en el contenedor `backend` (probe interno a `127.0.0.1:8000/api/health/`).
- **`depends_on`:** `nginx` → `backend` (`condition: service_healthy`); `backend` → `db` healthy. Nginx no arranca antes de Gunicorn listo.

### Validación operativa PROD-3 (jun 2026)

Sintaxis Nginx validada con Docker (sin levantar stack completo):

```bash
docker run --rm \
  --add-host backend:127.0.0.1 \
  -v "$(pwd)/deploy/nginx/nginx.prod.example.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine nginx -t
```

Resultado documentado: `syntax is ok` / `test is successful`.

`--add-host backend:127.0.0.1` resuelve el upstream `backend:8000` durante `nginx -t` fuera de la red Compose.

Map `X-Forwarded-Proto` (no pisa header del LB externo):

```nginx
map $http_x_forwarded_proto $proxy_x_forwarded_proto {
    default $http_x_forwarded_proto;
    ''      $scheme;
}
proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
```

### Headers proxy hacia Django

| Header | Origen Nginx |
|--------|----------------|
| `Host` | `$host` |
| `X-Real-IP` | `$remote_addr` |
| `X-Forwarded-For` | `$proxy_add_x_forwarded_for` |
| `X-Forwarded-Proto` | `$proxy_x_forwarded_proto` (map: preserva `$http_x_forwarded_proto` del LB; fallback `$scheme`) |

Django (`synesis/settings.py`): con `DJANGO_USE_PROXY_SSL_HEADER=True` → `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`.

### Variables Django / proxy

| Variable | Rol |
|----------|-----|
| `DJANGO_ALLOWED_HOSTS` | Debe incluir host público (`example.com`) **y** `DJANGO_HEALTHCHECK_HOST` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS del frontend (`https://app.example.com`) |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` en prod; evita loops si proxy envía `X-Forwarded-Proto: https` |
| `DJANGO_USE_PROXY_SSL_HEADER` | `True` cuando TLS termina delante de Gunicorn |
| `DJANGO_HEALTHCHECK_HOST` | Host del probe interno backend (p. ej. `localhost`) |

### Seguridad Nginx (plantilla)

- `/media/` **denegado** — no servir PHI como estática; usar endpoints protegidos Django.
- Dotfiles bloqueados (`location ~ /\.(?!well-known).*`).
- `client_max_body_size 25m` — uploads clínicos; ajustar con criterio operativo.
- Headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.
- HSTS comentado hasta TLS end-to-end validado.

### Tests estáticos (PROD-3 — CERRADO)

Clases `TestNginxProdExample` y `TestDockerComposeProdExample` en `api/tests/test_prod_runtime_config.py` — **39 tests** en suite runtime/healthcheck/nginx (incluye PROD-2-B).

---

## Migraciones

`RUN_MIGRATIONS=true` ejecuta `migrate --noinput` antes del runtime (patrón existente).

- **Dev Docker:** `RUN_MIGRATIONS=true` en `docker-compose.yml`
- **Prod:** job controlado; default `RUN_MIGRATIONS=false` en `docker-compose.prod.example.yml`

---

## Verificación automatizada (PROD-2-B — CERRADO)

Suite: `api/tests/test_prod_runtime_config.py` (**24 tests**).

| Caso | Qué valida |
|------|------------|
| Runtime inválido | `exit 1`, mensaje claro, sin secretos en salida |
| `runserver` | Invoca `manage.py runserver` con `BIND_ADDR` |
| `gunicorn` | Invoca `synesis.wsgi:application` con workers/timeout/bind |
| `RUN_MIGRATIONS=false` | No ejecuta `migrate` |
| `RUN_MIGRATIONS=true` | Intenta `migrate --noinput` (stub, sin DB real) |
| Seguridad | `SECRET_KEY` dummy no aparece en stdout/stderr |
| Compose dev/prod | `runserver` vs `gunicorn` en archivos de plantilla |
| Healthcheck prod | `/api/health/`, `DJANGO_HEALTHCHECK_HOST`, headers `Host` y `X-Forwarded-Proto`, sin curl/wget |

Técnica: stubs temporales de `nc`, `python`, `gunicorn` y `sleep` en `PATH`; no levanta servidores ni Postgres reales.

```bash
pytest api/tests/test_prod_runtime_config.py -q --reuse-db
```

Regresión mínima recomendada:

```bash
pytest api/tests/test_prod_settings_security.py api/tests/test_prod_runtime_config.py laboratorio/tests/test_lims_flujo_critico.py -q --reuse-db
```

---

## Auditoría de compose (pipelines / pre-release)

Usar **variables dummy** al validar la plantilla prod; nunca secretos reales ni `.env` productivo:

```bash
DJANGO_SECRET_KEY=dummy-secret \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,example.com \
DJANGO_HEALTHCHECK_HOST=localhost \
DJANGO_CORS_ALLOWED_ORIGINS=https://localhost \
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com \
DB_PASSWORD=dummy-password \
docker compose -f docker-compose.prod.example.yml config
```

Dev local:

```bash
docker compose config
```

---

## Storage privado / media clínica (PROD-4 — CERRADO)

### Cierre PROD-4 (evidencia, jun 2026)

**Archivos del commit PROD-4 (11 en total):**

| # | Archivo | Estado git |
|---|---------|------------|
| 1 | `deploy/nginx/nginx.prod.example.conf` | **untracked** — incluir en staging explícito |
| 2 | `api/tests/test_prod_runtime_config.py` | modified |
| 3 | `archivos_medicos/tests/test_api_security_c62.py` | modified |
| 4 | `docker-compose.prod.example.yml` | modified |
| 5 | `.env.production.example` | modified |
| 6 | `docs_synesis/PROD_RUNTIME.md` | modified |
| 7 | `docs_synesis/PROD_CHECKLIST.md` | modified |
| 8 | `docs_synesis/DOC_BACKEND.md` | modified |
| 9 | `docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md` | modified |
| 10 | `docs_synesis/DOC_TESTS.md` | modified |
| 11 | `docs_synesis/DOC_PERMISOS_AUDITORIA.md` | modified |

`git diff --stat` muestra **10 files changed** (solo tracked); el undécimo (`deploy/nginx/...`) aparece como `?? deploy/` hasta hacer `git add` explícito. **No usar `git add ..`.**

**Staging explícito sugerido:**

```bash
git add api/tests/test_prod_runtime_config.py \
  archivos_medicos/tests/test_api_security_c62.py \
  deploy/nginx/nginx.prod.example.conf \
  docker-compose.prod.example.yml \
  .env.production.example \
  docs_synesis/PROD_RUNTIME.md \
  docs_synesis/PROD_CHECKLIST.md \
  docs_synesis/DOC_BACKEND.md \
  docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md \
  docs_synesis/DOC_TESTS.md \
  docs_synesis/DOC_PERMISOS_AUDITORIA.md
```

**Implementado y validado (sin impacto EMR/LIMS — sin modelos, migraciones, permisos funcionales ni frontend):**

| Entregable | Evidencia |
|------------|-----------|
| Nginx `/media/` bloqueado | `deploy/nginx/nginx.prod.example.conf` — `deny all; return 404` |
| Django no sirve media en prod | `synesis/urls.py` — `static(MEDIA_URL)` solo si `DEBUG=True` |
| Compose prod sin media en Nginx | `docker-compose.prod.example.yml` — volumen media solo comentado en `backend` |
| Endpoints seguros documentados | Ver tabla abajo |
| Tests estáticos PROD-4 | `TestProdPrivateMediaStorage`, tests Nginx alias/autoindex en `test_prod_runtime_config.py` |
| Tests permisos archivos | `archivos_medicos/tests/test_api_security_c62.py` — anónimo bloqueado |
| `.env.production.example` | Sección PROD-4; sin credenciales S3/MinIO |

### Política productiva

1. **`MEDIA_ROOT`** (`synesis/settings.py` → `BASE_DIR / 'media'`) vive en el contenedor **backend** o volumen Docker **interno**; nunca montado en Nginx.
2. **`MEDIA_URL=/media/`** no es mecanismo de autorización; en producción Nginx y Django (`DEBUG=False`) **no** sirven archivos por esa ruta.
3. **Descargas** vía API autenticada con `FileResponse` y permisos por rol/objeto.
4. **Desarrollo:** `DEBUG=True` monta `/media/` en `synesis/urls.py` — solo local; no replicar en prod.
5. **Object storage (S3/MinIO):** fase posterior si no hay infraestructura previa; sin credenciales en repo.

### FileField auditados (sin cambios de modelo)

| Modelo / campo | Upload path | Descarga segura |
|----------------|-------------|-----------------|
| `emr.Documento.archivo` | `emr/documentos/` | `GET /api/documentos/{id}/download/` — autenticado, permisos por atención |
| `archivos_medicos.ArchivoMedico.archivo` | `archivos_medicos/%Y/%m/%d/` | `GET /api/archivos-medicos/archivos/{id}/download/` |
| `estudios` informe PDF | `estudios/informes/` | `GET /api/estudios-complementarios/.../download-pdf/` |
| `turnos.RegistroProcedimiento.adjunto_resultado` | `emr/procedimientos/` | `GET /api/registros-procedimientos/{id}/download-adjunto-resultado/` — autenticado, `IsEMRClinicianOrReadOnly` + `get_queryset` |
| `turnos.RegistroQuirurgico.consentimiento_informado` | `emr/consentimientos/` | `GET /api/registros-quirurgicos/{id}/download-consentimiento-informado/` — idem |

### Endpoints de descarga — estado de seguridad

| Endpoint | Auth | Permisos | Sin `/media/` en API |
|----------|------|----------|----------------------|
| `/api/archivos-medicos/archivos/{id}/download/` | Sí (`IsAuthenticated`) | Rol + paciente/médico | Sí (`download_url` relativo) |
| `/api/documentos/{id}/download/` | Sí | Atención / rol EMR | Sí |
| LIMS `informe_pdf` | Sí | `LimsSolicitudExamenPermission` | Sí (PDF en memoria/blob) |
| Estudios complementarios PDF/archivos | Sí | `estudios` access | Sí |
| `/api/registros-procedimientos/{id}/download-adjunto-resultado/` | Sí | `IsEMRClinicianOrReadOnly` + `get_queryset` | Sí (`adjunto_resultado_download_url`) |
| `/api/registros-quirurgicos/{id}/download-consentimiento-informado/` | Sí | Idem | Sí (`consentimiento_informado_download_url`) |
| `tipos_archivo_publicos` | `AllowAny` | Catálogo estático sin PHI | N/A |

### Cierre PROD-4-A (evidencia, jun 2026) — **CERRADO**

Descarga autenticada de `RegistroProcedimiento.adjunto_resultado` y `RegistroQuirurgico.consentimiento_informado`. Sin cambios en modelos, migraciones, permisos EMR/LIMS, reglas clínicas, estados ni frontend.

| Entregable | Evidencia |
|------------|-----------|
| `GET /api/registros-procedimientos/{id}/download-adjunto-resultado/` | `RegistroProcedimientoViewSet.download_adjunto_resultado`; `self.get_object()`; `FileResponse`; `Content-Disposition` con basename; 404 si falta archivo |
| `GET /api/registros-quirurgicos/{id}/download-consentimiento-informado/` | `RegistroQuirurgicoViewSet.download_consentimiento_informado`; idem |
| Serializers sin `/media/` | `adjunto_resultado` / `consentimiento_informado` write-only; lectura: `*_nombre`, `*_download_url` |
| Permisos | `IsEMRClinicianOrReadOnly` + `get_queryset()` existentes; anónimo 401/403; ajeno 403/404 |
| Tests | `api/tests/test_registro_adjuntos_download_prod4a.py` — **15 passed** |
| Regresión mínima | **106 passed** (seguridad + runtime + LIMS crítico + archivos médicos) |
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| Compose dev/prod + `nginx -t` | OK |
| `git diff --check` | OK |

**Archivos del commit PROD-4-A (10 — staging explícito, sin `git add ..`):**

- `api/views.py`
- `api/serializers.py`
- `api/tests/test_registro_adjuntos_download_prod4a.py`
- `docs_synesis/DOC_API_ENDPOINTS.md`
- `docs_synesis/DOC_BACKEND.md`
- `docs_synesis/DOC_PERMISOS_AUDITORIA.md`
- `docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md`
- `docs_synesis/DOC_TESTS.md`
- `docs_synesis/PROD_CHECKLIST.md`
- `docs_synesis/PROD_RUNTIME.md`

**No mezclar en staging PROD-4-A:** `.env.production.example`, `docker-compose.prod.example.yml`, `api/tests/test_prod_runtime_config.py`, `archivos_medicos/tests/test_api_security_c62.py`, `deploy/` (alcance PROD-3/PROD-4).

**Frontend (restricción, sin cambios):** no consumir `FileField.url` ni `/media/`; usar `adjunto_resultado_download_url` / `consentimiento_informado_download_url`.

### Cierre PROD-4-B (evidencia, jun 2026) — **CERRADO**

Auditoría mínima en descargas exitosas (`_audit_turnos_registro_download` → `log_event` vía `_safe_audit_documento`; patrón Documento/ArchivoMedico/LIMS PDF). `action='UPDATE'`, `module='turnos'`, `after=None`. Solo descargas exitosas; no autorizado/sin archivo no audita.

| Metadata `accion` | `field` | `endpoint` | `view` |
|-------------------|---------|------------|--------|
| `registro_procedimiento_adjunto_download` | `adjunto_resultado` | `download-adjunto-resultado` | `RegistroProcedimientoViewSet.download_adjunto_resultado` |
| `registro_quirurgico_consentimiento_download` | `consentimiento_informado` | `download-consentimiento-informado` | `RegistroQuirurgicoViewSet.download_consentimiento_informado` |

**No se registra:** path absoluto, `/media/`, filename, contenido, URL pública, PHI innecesaria.

**Observación técnica:** acción semántica `DOWNLOAD` evaluable a futuro; esta fase preserva `action='UPDATE'` del patrón vigente.

**Archivos commit PROD-4-B (staging explícito):**

- `api/views.py`
- `api/tests/test_registro_adjuntos_download_audit_prod4b.py`
- `docs_synesis/DOC_API_ENDPOINTS.md`, `DOC_BACKEND.md`, `DOC_PERMISOS_AUDITORIA.md`, `DOC_RIESGOS_DEUDA_TECNICA.md`, `DOC_TESTS.md`, `PROD_CHECKLIST.md`, `PROD_RUNTIME.md`

**No mezclar:** archivos PROD-3/4/4-A listados en sección PROD-4-A.

### Tests PROD-4-A / PROD-4-B (evidencia jun 2026)

| Suite | Resultado |
|-------|-----------|
| `api/tests/test_registro_adjuntos_download_prod4a.py` | **15 passed** |
| `api/tests/test_registro_adjuntos_download_audit_prod4b.py` | **6 passed** |
| Regresión mínima (+ PROD-4-A) | **121 passed** |

```bash
./emr_env/bin/pytest api/tests/test_registro_adjuntos_download_audit_prod4b.py -q --reuse-db
./emr_env/bin/pytest api/tests/test_registro_adjuntos_download_prod4a.py -q --reuse-db
./emr_env/bin/pytest api/tests/test_prod_settings_security.py api/tests/test_prod_runtime_config.py laboratorio/tests/test_lims_flujo_critico.py archivos_medicos/tests/ api/tests/test_registro_adjuntos_download_prod4a.py -q --reuse-db
```

---

## PROD-5 — Backups y restore — **CERRADO** (jun 2026)

Estrategia versionada **sin jobs automáticos en compose** ni restore destructivo ejecutado en esta fase.

| Script | Propósito |
|--------|-----------|
| `deploy/backup/backup_postgres.example.sh` | `pg_dump` custom + `sha256sum` |
| `deploy/backup/backup_media.example.sh` | `tar.gz` de `MEDIA_ROOT` + checksum |
| `deploy/backup/restore_postgres.example.sh` | `pg_restore` con `CONFIRM_RESTORE=true`, `RESTORE_TARGET_DB`, `BACKUP_FILE` |
| `deploy/backup/README.md` | DB + media obligatorios; restore drill staging; cifrado/offsite operador |

**Recuperación completa:** PostgreSQL **y** media clínica (PROD-4).

**Seguridad:** `.gitignore` excluye artefactos; sin PHI/secretos en plantillas; restore bloquea `synesis_db` por defecto — operador debe evitar cualquier DB/host productivo real.

**Artefacto local:** `./backup_pendrive.sql` puede existir en disco, está en `.gitignore` y **no trackeado**; si contiene datos sensibles, mover fuera del repo y no commitear.

### Evidencia de cierre (jun 2026)

| Validación | Resultado |
|------------|-----------|
| `bash -n` (3 scripts) | OK |
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sin cambios |
| `test_prod_backup_config.py` | **31 passed** |
| `test_prod_runtime_config.py` + PROD-5 | **80 passed** |
| Regresión mínima | **127 passed** |
| Compose dev/prod | OK |
| `nginx -t` | OK |
| `git diff --check` | OK |
| Restore real ejecutado | **No** |
| Backups PROD-5 versionados | **No** |

**Archivos commit PROD-5 (staging explícito, sin `git add ..`):**

- `deploy/backup/backup_postgres.example.sh`
- `deploy/backup/backup_media.example.sh`
- `deploy/backup/restore_postgres.example.sh`
- `deploy/backup/README.md`
- `.gitignore`
- `api/tests/test_prod_backup_config.py`
- `docs_synesis/PROD_RUNTIME.md`
- `docs_synesis/PROD_CHECKLIST.md`
- `docs_synesis/DOC_BACKEND.md`
- `docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md`
- `docs_synesis/DOC_TESTS.md`
- `.env.production.example`

**No mezclar:** PROD-4/4-A/4-B (`api/views.py`, serializers, tests turnos, `test_prod_runtime_config.py` ampliado por PROD-4, etc.).

**Fuera de alcance PROD-5:** cron en compose, S3/MinIO, cifrado offsite en scripts, scheduling externo, **ejecución real del drill en infra productiva**, WAF, monitoreo externo, TLS/ACME.

---

## PROD-5-A — Restore drill staging (jun 2026)

Documentación y verificación **no destructiva**; no se ejecuta restore real en el repo.

| Entregable | Ruta |
|------------|------|
| Procedimiento drill | `deploy/backup/RESTORE_DRILL_STAGING.md` |
| Verificación post-restore | `deploy/backup/verify_restore.example.sh` |
| Tests estáticos | `api/tests/test_prod_restore_drill_config.py` |

**Exige:** staging/temporal, `CONFIRM_RESTORE=true`, `RESTORE_TARGET_DB`, `BACKUP_FILE`, `MEDIA_RESTORE_DIR`, checksums, media privada, `/media/` bloqueado, evidencia sin PHI fuera del repo.

**Staging sugerido PROD-5-A:** `RESTORE_DRILL_STAGING.md`, `verify_restore.example.sh`, `test_prod_restore_drill_config.py`, docs actualizadas. No mezclar con PROD-4/4-A/4-B si commits separados.

---

## PROD-8 — Checklist pre-piloto productivo (jun 2026)

Documentación operativa para decisión **GO / NO-GO** antes de un piloto productivo técnico controlado. **Sin cambios de runtime ejecutable** en esta fase.

| Entregable | Ruta |
|------------|------|
| Checklist pre-piloto | `docs_synesis/PROD_PREPILOT_CHECKLIST.md` |
| Tests documentales | `api/tests/test_prod_prepilot_checklist.py` |

**Cubre:** `DEBUG=False`, secretos fuera del repo, `ALLOWED_HOSTS`, CSRF/CORS, TLS/proxy, `/media/` privada, backups/restore drill, monitoreo mínimo (definición), rollback, usuarios/roles, datos sintéticos, evidencia sanitizada, frontend en despliegue separado.

**No habilita:** producción clínica abierta ni validación UX frontend productiva.

**Siguiente fase recomendada:** **PROD-9** — Observabilidad mínima (completada); luego **PROD-10** runbook piloto.

---

## PROD-9 — Observabilidad mínima (jun 2026)

Plan operativo de observabilidad para piloto técnico controlado. **Sin cambios de runtime ejecutable** obligatorios en esta fase.

| Entregable | Ruta |
|------------|------|
| Documentación observabilidad | `docs_synesis/PROD_OBSERVABILITY_MIN.md` |
| Checks no destructivos | `deploy/observability/check_observability.example.sh` |
| README operador | `deploy/observability/README.md` |
| Tests documentales | `api/tests/test_prod_observability_min.py` |

**Cubre:** logs backend/Gunicorn, Nginx, PostgreSQL; errores 4xx/5xx; healthcheck `GET /api/health/`; contenedores; DB; disco; backups; incidentes; evidencia sanitizada.

**No habilita:** producción clínica abierta ni APM externo obligatorio (recomendado al operador).

**Siguiente fase recomendada:** **PROD-10** — Piloto técnico controlado (runbook + evidencia externa).

---

## PROD-10 — Piloto técnico controlado (jun 2026)

Runbook de ejecución del piloto técnico aplicando PROD-8 + PROD-9. **Sin cambios de runtime ejecutable** obligatorios.

| Entregable | Ruta |
|------------|------|
| Runbook piloto | `docs_synesis/PROD_TECHNICAL_PILOT_RUNBOOK.md` |
| Plantilla evidencia | `docs_synesis/PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md` |
| Smoke piloto | `deploy/smoke/prod_technical_pilot.example.sh` |
| Tests documentales | `api/tests/test_prod_technical_pilot.py` |

**Cubre:** ventana piloto, PROD-8/9, smoke anónimo/autenticado, evidencia sanitizada fuera del repo, GO/NO-GO, rollback.

**No habilita:** producción clínica abierta. Ejecución real del piloto = evidencia externa del operador.

**Siguiente fase recomendada:** **PROD-12** — Autorización institucional y piloto datos reales mínimos (documental).

---

## PROD-11 — Revisión post-piloto (jun 2026)

Revisión formal posterior al piloto técnico real (PROD-10). **Sin cambios de runtime ejecutable.**

| Entregable | Ruta |
|------------|------|
| Guía revisión | `docs_synesis/PROD_POST_PILOT_REVIEW.md` |
| Plantilla acciones | `docs_synesis/PROD_POST_PILOT_ACTIONS_TEMPLATE.md` |
| Tests documentales | `api/tests/test_prod_post_pilot_review.py` |

**Cubre:** evidencia externa, GO/NO-GO post-piloto, PROD-8/9/10, observabilidad, incidentes, acciones correctivas, criterios datos reales mínimos.

**No habilita:** producción clínica abierta ni autorizaciones reales en repo.

**Siguiente fase recomendada:** hardening operativo sostenido y validación frontend/TLS/APM — **producción clínica abierta fuera de alcance**.

---

## PROD-12 — Autorización institucional y piloto datos reales mínimos (jun 2026)

Marco documental para evaluar autorización institucional externa y piloto acotado con datos reales mínimos. **Sin cambios de runtime ejecutable.**

| Entregable | Ruta |
|------------|------|
| Guía autorización / piloto mínimo | `docs_synesis/PROD_MIN_REAL_DATA_AUTH.md` |
| Plantilla alcance | `docs_synesis/PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md` |
| Tests documentales | `api/tests/test_prod_min_real_data_auth.py` |

**Cubre:** GO post-piloto PROD-11, acciones críticas cerradas, autorización externa, responsables, alcance funcional limitado, módulos/roles/usuarios, datos permitidos/prohibidos, ventana limitada, suspensión, incidentes, rollback, backups PROD-7, observabilidad PROD-9, `/media/` privado, APIs protegidas, frontend separado.

**No habilita:** producción clínica abierta ni piloto real con datos mínimos hasta acta y autorización **fuera del repo**.

**Siguiente fase recomendada:** **PROD-13** — Hardening operativo sostenido (completada documentalmente); luego evaluación ampliación alcance / object storage — **producción clínica abierta fuera de alcance**.

---

## PROD-13 — Hardening operativo sostenido (jun 2026)

Marco documental para sostener operación segura posterior a PROD-12. **Sin cambios de runtime ejecutable.**

| Entregable | Ruta |
|------------|------|
| Guía hardening sostenido | `docs_synesis/PROD_OPERATIONAL_HARDENING.md` |
| Plantilla alertas | `docs_synesis/PROD_MONITORING_ALERTS_TEMPLATE.md` |
| Runbook rotación secretos | `docs_synesis/PROD_SECRET_ROTATION_RUNBOOK.md` |
| Tests documentales | `api/tests/test_prod_operational_hardening.py` |

**Cubre:** monitoreo externo/APM (Sentry, Datadog, Prometheus/Grafana), alertas, señales críticas, rotación secretos, TLS, headers, WAF/rate limiting, mantenimiento recurrente, frontend separado, evidencia sanitizada.

**No habilita:** producción clínica abierta ni despliegue real de APM hasta configuración **fuera del repo**.

---

## Pendiente post-PROD-5

- ~~Nginx / reverse proxy como servicio compose~~ — **PROD-3**
- ~~Storage privado política + bloqueo `/media/`~~ — **PROD-4**
- Certificados TLS reales / automatización ACME (montar fuera del repo)
- Object storage real (S3/MinIO) con credenciales en gestor de secretos
- ~~Endpoints `download/` para `adjunto_resultado` y `consentimiento_informado`~~ — **PROD-4-A**
- ~~Backups / restore (plantillas versionadas)~~ — **PROD-5**
- ~~WAF / rate limiting~~ — **PROD-13 documentado**; despliegue/validación real: operador
- ~~Monitoreo externo (Sentry/Datadog/Prometheus)~~ — **PROD-13 documentado**; despliegue real pendiente operador
- ~~Rotación de secretos~~ — **PROD-13 runbook documentado**; ejecución real: operador

---

## Referencias

- `docs_synesis/PROD_CHECKLIST.md`
- `docs_synesis/PROD_PREPILOT_CHECKLIST.md` (PROD-8)
- `docs_synesis/PROD_OBSERVABILITY_MIN.md` (PROD-9)
- `docs_synesis/PROD_TECHNICAL_PILOT_RUNBOOK.md` (PROD-10)
- `docs_synesis/PROD_POST_PILOT_REVIEW.md` (PROD-11)
- `docs_synesis/PROD_MIN_REAL_DATA_AUTH.md` (PROD-12)
- `docs_synesis/PROD_OPERATIONAL_HARDENING.md` (PROD-13)
- `entrypoint.sh`
- `docker-compose.yml` (dev)
- `deploy/nginx/nginx.prod.example.conf` (plantilla Nginx PROD-3)
