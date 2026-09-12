# Reglas — Entorno local (una sola base)

**SoT de arranque:** `docs/dev-start.md`, `bash scripts/verify_local_db.sh`.  
Este archivo es la **política**. El how-to vive en `docs/dev-start.md`.

Desarrollo local = **solo** Postgres Docker `emr_postgres` / `synesis_db` / `postgres` @ `localhost:5432`.

Mezclar bases es un error grave (PHI, datos clínicos, falsa sensación de backup).

## Permitido vs prohibido

| Permitido | Prohibido (sin confirmación explícita del usuario) |
|-----------|-----------------------------------------------------|
| Postgres solo en contenedor `emr_postgres` | Postgres nativo WSL / usuario `synesis_user` |
| `./emrctl up` (db + backend Docker) | Cambiar `.env` a otra BD |
| `DB_HOST=localhost`, `DB_USER=postgres`, `DB_NAME=synesis_db` | Credenciales distintas a `docker-compose.yml` |
| Backup con `bash scripts/backup_postgres_local.sh` antes de restores | `docker compose down -v` sin advertencia fuerte |
| Restore con `scripts/restore_docker_db.sh` + confirmación | `DROP DATABASE` / restore destructivo sin backup y OK del usuario |

El stack **demo** (`docker-compose.demo.yml`, puerto 8081) es otro volumen; no es la BD clínica. Ver `docs/demo-stack.md`.

## Antes de tocar `.env`, DB o Docker

1. No cambiar `DB_*` para “arreglar” un error de conexión sin decir qué base se usará y qué datos implica.
2. No sugerir `runserver` manual como flujo principal; el estándar es `./emrctl up`.
3. Si hay error de autenticación PostgreSQL, investigar si Docker vs nativo compiten en `:5432` antes de cambiar contraseñas.
4. Restore o reset: backup primero, confirmación del usuario, explicar qué se pierde y qué se recupera.
5. Tras restore de dump: `./emrctl seed` + `poblar_todos_catalogos` (los catálogos clínicos no vienen en todos los dumps).
