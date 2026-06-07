# PROD_CHECKLIST — Despliegue inicial SYNESIS EMR/LIMS

**Fase:** PROD-1 (jun 2026) — hardening mínimo de configuración  
**Alcance:** checklist operativo; no sustituye auditoría de seguridad ni despliegue completo.

---

## Antes del primer despliegue

### Variables de entorno obligatorias (`DEBUG=False`)

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` — valor largo aleatorio (no `change-me`, no `django-insecure-*`, no `dev_secret_key_change_me`)
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
- [ ] Volúmenes persistentes para Postgres y media/storage privado

---

## Comandos de verificación pre-release

```bash
./emr_env/bin/python manage.py check
./emr_env/bin/python manage.py makemigrations --check --dry-run
./emr_env/bin/pytest api/tests/test_prod_settings_security.py -q --reuse-db
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
- Job de backups/restore documentado
- `gunicorn`/`uvicorn` + workers (entrypoint actual es `runserver` solo dev)
- Storage object privado (S3/MinIO) para media clínica
- npm audit / dependabot frontend (no ejecutar `npm audit fix` automático en PROD-1)

---

## Referencias

- `docs_synesis/DOC_BACKEND.md` — configuración PROD-1
- `docs_synesis/DOC_PERMISOS_AUDITORIA.md` — permisos y auditoría
- `docs_synesis/DOC_RIESGOS_DEUDA_TECNICA.md` — riesgos residuales
- `.env.production.example` — plantilla de variables
