# PROD-6 — Readiness productivo controlado / Smoke E2E (backend/API)

**Fase:** PROD-6 — piloto técnico controlado
**Estado:** documentación + validaciones no destructivas
**Fecha:** junio 2026

---

## Alcance

Preparar un **paquete repetible** para la primera prueba seria del backend SYNESIS EMR/LIMS en un entorno **productivo controlado** (staging/pilot), integrando fases ya cerradas:

| Fase | Qué valida el smoke |
|------|---------------------|
| PROD-2-B | Gunicorn + `GET /api/health/` |
| PROD-3/4 | Nginx reverse proxy; `/media/` bloqueado |
| PROD-4-A | Descargas protegidas adjuntos turnos |
| PROD-4-B | Auditoría de descargas exitosas |
| PROD-5/5-A | Backup/restore drill documentado (sin restore real en smoke) |
| PROD-1/1-A | Secret key, CORS, CSRF, `DEBUG=False` |

**Objetivo:** confirmar que el stack productivo **puede operar junto** antes de un piloto clínico controlado.

**No es:** producción clínica abierta, go-live de usuarios finales ni validación de frontend SPA.

---

## Fuera de alcance

- Deploy real a producción viva desde este repo.
- Restore real de backups.
- Datos reales de pacientes en smoke inicial (**usar solo datos sintéticos**).
- PHI en evidencia, logs, capturas o commits.
- Frontend SPA (no versionado en este repo).
- S3/MinIO, TLS/ACME real, WAF, monitoreo externo, cron.
- Nuevos modelos, migraciones, endpoints, permisos o reglas clínicas.

---

## Precondiciones (operador)

1. Entorno **aislado** (staging/pilot), no producción clínica activa.
2. Variables de `.env.production.example` aplicadas con **secretos reales fuera del repo**.
3. `DJANGO_DEBUG=False`, `DJANGO_RUNTIME=gunicorn`.
4. Postgres y backend healthy; Nginx expone `:80` (o TLS terminado upstream).
5. Usuarios de prueba **sintéticos** creados por operador (no commitear credenciales).
6. Sin backups, dumps ni `.sql` en el working tree del repo.

Referencias: `PROD_RUNTIME.md`, `PROD_CHECKLIST.md`, `deploy/nginx/nginx.prod.example.conf`, `docker-compose.prod.example.yml`.

---

## Variables de entorno a revisar (checklist)

| Variable | Revisión |
|----------|----------|
| `DJANGO_SECRET_KEY` | Fuerte; no placeholder |
| `DJANGO_ALLOWED_HOSTS` | Hosts explícitos; incluye `DJANGO_HEALTHCHECK_HOST` |
| `DJANGO_HEALTHCHECK_HOST` | Coincide con healthcheck compose |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Orígenes HTTPS del cliente real |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes que envían cookies CSRF |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` si TLS activo |
| `DJANGO_USE_PROXY_SSL_HEADER` | `True` detrás de Nginx/LB |
| `DB_*` | Postgres de staging; no credenciales en repo |

---

## Matriz mínima de roles (smoke sintético)

| Rol | Smoke mínimo esperado |
|-----|------------------------|
| **Anónimo** | `401/403` en endpoints protegidos; `/media/` no accesible vía Nginx |
| **admin** | Login OK; `GET /api/auditoria/events/` permitido (si staff) |
| **medico** | Login OK; listados EMR autorizados; descarga adjunto propio OK |
| **paciente** | Login OK; solo datos propios; descarga adjunto propio si aplica |
| **laboratorio** | Login OK; LIMS operativo; **bloqueado** en adjuntos EMR turnos |
| **secretaria** (opc.) | Según permisos vigentes en listados |
| **enfermeria** (opc.) | Según permisos vigentes |

No usar cuentas ni DNI reales en la primera ronda de smoke.

---

## Smoke E2E backend/API (manual)

### 1. Infraestructura

```bash
docker compose -f docker-compose.prod.example.yml config   # vars dummy localmente
docker run --rm --add-host backend:127.0.0.1 \
  -v "$PWD/deploy/nginx/nginx.prod.example.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine nginx -t
curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/api/health/"
# Esperado: 200
curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/media/"
# Esperado: 403 o 404 (Nginx deny)
```

### 2. Autenticación (usuario sintético)

```bash
# Credenciales vía entorno; nunca en repo
curl -sS -X POST "$BASE_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$SMOKE_USERNAME\",\"password\":\"$SMOKE_PASSWORD\"}"
curl -sS "$BASE_URL/api/auth/current-user/" -H "Authorization: Bearer $TOKEN"
curl -sS -X POST "$BASE_URL/api/auth/logout/" -H "Authorization: Bearer $TOKEN"
```

No imprimir tokens completos en evidencia.

### 3. Endpoints críticos (GET, sin PHI)

| Endpoint | Rol | Esperado |
|----------|-----|----------|
| `/api/pacientes/` | medico/admin | 200 o lista filtrada |
| `/api/turnos/` | medico | 200 |
| `/api/atenciones/` | medico | 200 |
| `/api/lab/solicitudes/` | laboratorio | 200 |
| `/api/laboratorio/solicitudes/` | laboratorio | 200 |
| `/api/auditoria/events/` | admin | 200 |
| `/api/registros-procedimientos/{id}/download-adjunto-resultado/` | medico propio | 200 + attachment |
| `/api/registros-quirurgicos/{id}/download-consentimiento-informado/` | medico propio | 200 + attachment |

Usar IDs de registros **sintéticos** creados en staging.

### 4. Seguridad

- Anónimo → `401/403` en rutas protegidas.
- Paciente → no accede a datos ajenos.
- Médico ajeno → `403/404` en descarga adjunto ajeno.
- Laboratorio → `403/404` en descarga adjunto EMR turnos.
- JSON de serializers **sin** `/media/`.

### 5. Auditoría (PROD-4-B)

Tras descarga autorizada exitosa:

- Existe `AuditEvent` con `metadata.accion` = `registro_procedimiento_adjunto_download` o `registro_quirurgico_consentimiento_download`.
- Metadata **sin** path, filename, `/media/` ni contenido.

Tests automatizados: `test_registro_adjuntos_download_audit_prod4b.py`.

### 6. Backup / restore drill (solo checklist)

- [ ] Plantillas `deploy/backup/*.example.sh` presentes.
- [ ] `RESTORE_DRILL_STAGING.md` revisado.
- [ ] Backups fuera del repo; checksums OK.
- [ ] **No ejecutar restore real** en este smoke inicial salvo drill formal en staging aislado.

---

## Script automatizado (opcional)

`deploy/smoke/prod_readiness_smoke.example.sh` — smoke remoto no destructivo.

Requisitos: `BASE_URL`; credenciales opcionales vía `SMOKE_USERNAME` / `SMOKE_PASSWORD`. Solo entorno controlado.

```bash
bash -n deploy/smoke/prod_readiness_smoke.example.sh
export BASE_URL=https://staging.example.com
export SMOKE_USERNAME=pilot_medico_sintetico
export SMOKE_PASSWORD='...'   # gestor de secretos; no commitear
./deploy/smoke/prod_readiness_smoke.example.sh
```

---

## Validaciones automáticas (repo local)

```bash
./emr_env/bin/python manage.py check
./emr_env/bin/python manage.py makemigrations --check --dry-run
./emr_env/bin/pytest api/tests/test_prod_readiness_smoke.py -q --reuse-db
./emr_env/bin/pytest \
  api/tests/test_prod_settings_security.py \
  api/tests/test_prod_runtime_config.py \
  laboratorio/tests/test_lims_flujo_critico.py \
  archivos_medicos/tests/ \
  api/tests/test_registro_adjuntos_download_prod4a.py \
  api/tests/test_registro_adjuntos_download_audit_prod4b.py \
  -q --reuse-db
```

---

## Criterios GO / NO-GO

### GO (piloto técnico controlado)

- [ ] `manage.py check` OK en staging.
- [ ] Healthcheck 200 detrás de Nginx.
- [ ] `/media/` bloqueado (Nginx + Django prod).
- [ ] Login/logout/current-user OK con usuario sintético.
- [ ] Roles críticos respetan permisos (matriz arriba).
- [ ] Descarga protegida + auditoría OK (tests PROD-4-A/B en CI + smoke manual).
- [ ] Regresión mínima repo pasa.
- [ ] Backup templates + drill doc revisados.
- [ ] Evidencia sin PHI.

### NO-GO (detener piloto)

- Secretos placeholder o en repo.
- `/media/` accesible públicamente.
- Anónimo accede a datos clínicos.
- Descarga sin auditoría en entorno que debería tener PROD-4-B.
- Restore ejecutado contra base productiva.
- Smoke con PHI real sin autorización formal.
- Frontend asumido OK sin validar repo/UI real.

---

## Runbook de reversión (piloto)

1. **Detener tráfico:** quitar DNS o balanceador hacia el entorno pilot.
2. **Detener stack:** `docker compose -f docker-compose.prod.example.yml down` (staging).
3. **No borrar datos** hasta post-mortem acordado.
4. **Restaurar versión anterior:** redeploy imagen/tag previo conocido.
5. **Verificar health** en versión anterior antes de reabrir tráfico limitado.
6. **Registrar incidente** fuera del repo (sin PHI).
7. **No ejecutar** `pg_restore` / `dropdb` salvo procedimiento formal PROD-5 en staging.

---

## Evidencia

### Permitida (fuera del repo)

- Fecha, entorno, versión commit/imagen.
- Códigos HTTP, conteos agregados.
- Resultado GO/NO-GO por ítem checklist.
- IDs sintéticos de prueba (no DNI reales).

### Prohibida

- PHI, DNI, nombres de pacientes reales.
- Tokens, cookies, passwords completos.
- Paths internos, filenames clínicos, dumps, capturas con datos.
- Backups en git.

---

## Frontend

**No hay frontend SPA versionado en este repositorio.** PROD-6 valida backend/API y operación productiva controlada. Un piloto con usuarios finales requiere:

1. Confirmar frontend real en otro repo/despliegue.
2. Auditar UI antes de producción clínica abierta.

---

## Transición de fases

| Etapa | Descripción |
|-------|-------------|
| **Piloto técnico** | PROD-6 smoke backend; datos sintéticos |
| **Piloto clínico controlado** | Datos reales mínimos autorizados; supervisión operativa |
| **Producción clínica abierta** | **Fuera de alcance PROD-6** — requiere go-live formal, frontend, legal, backups operativos |

---

## Referencias

- `PROD_CHECKLIST.md` — sección PROD-6
- `PROD_RUNTIME.md`
- `deploy/backup/RESTORE_DRILL_STAGING.md`
- `DOC_PERMISOS_AUDITORIA.md`
- `DOC_API_ENDPOINTS.md`
- `api/tests/test_prod_readiness_smoke.py`
