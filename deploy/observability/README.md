# PROD-9 — Observabilidad mínima (plantillas operativas)

Scripts y documentación para **checks no destructivos** en entorno staging/pilot controlado.

## Alcance

| Script | Propósito |
|--------|-----------|
| `check_observability.example.sh` | Verificación local: contenedores, health HTTP, disco, DB reachability |

**No ejecutar contra producción clínica activa sin autorización.** No incluye credenciales ni PHI.

## Variables (operador)

| Variable | Descripción |
|----------|-------------|
| `BASE_URL` | URL del proxy piloto (ej. `http://127.0.0.1`) — sin barra final |
| `BACKEND_CONTAINER` | Nombre contenedor backend (default: `emr_backend_prod`) |
| `NGINX_CONTAINER` | Nombre contenedor nginx (default: `emr_nginx_prod`) |
| `DB_CONTAINER` | Nombre contenedor PostgreSQL (default: `emr_postgres_prod`) |

## Uso

```bash
export BASE_URL="http://127.0.0.1"
bash deploy/observability/check_observability.example.sh
```

Validar sintaxis:

```bash
bash -n deploy/observability/check_observability.example.sh
```

## Fuera de alcance

- Restore de backups.
- `docker compose down -v`, `rm -rf`, `dropdb`.
- Impresión de passwords, tokens o contenido de logs clínicos.
- Monitoreo externo Sentry/Datadog (documentado en `PROD_OBSERVABILITY_MIN.md`).

## Referencias

- `docs_synesis/PROD_OBSERVABILITY_MIN.md`
- `deploy/smoke/prod_readiness_smoke.example.sh`
