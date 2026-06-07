# PROD_RUNTIME — Runtime backend SYNESIS EMR/LIMS

**Fase:** PROD-2-A (jun 2026)  
**Alcance:** selección de runtime WSGI (dev vs prod); sin Nginx ni storage privado en esta fase.

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

---

## Migraciones

`RUN_MIGRATIONS=true` ejecuta `migrate --noinput` antes del runtime (patrón existente).

- **Dev Docker:** `RUN_MIGRATIONS=true` en `docker-compose.yml`
- **Prod:** job controlado; default `RUN_MIGRATIONS=false` en `docker-compose.prod.example.yml`

---

## Pendiente post-PROD-2-A

- Nginx / reverse proxy como servicio compose
- Storage privado para media clínica
- Backups / restore automatizados
- WAF / rate limiting
- Health checks HTTP sobre Gunicorn en orquestador

---

## Referencias

- `docs_synesis/PROD_CHECKLIST.md`
- `entrypoint.sh`
- `docker-compose.yml` (dev)
- `docker-compose.prod.example.yml` (plantilla prod)
