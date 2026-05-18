# Arranque local EMR + LIMS (desarrollo)

`docs_synesis/` documenta el sistema en producción/diseño. Este archivo describe **cómo levantar el stack en tu máquina** para probar con distintos usuarios.

## Requisitos

- Python virtualenv en `emr_env/` (raíz del repo)
- Node.js y `npm` en `PATH` (sin rutas absolutas; nvm u otro gestor es válido)
- `cd frontend && npm install` (una vez)
- PostgreSQL en `:5432` (instalación local **o** contenedor Docker)

## Comandos

```bash
# Backend + frontend (Postgres ya debe estar escuchando en :5432)
./emr-start

# Levantar solo la DB con Docker Compose
START_DB=true ./emr-start

# Migraciones (default) + usuarios/catálogos demo idempotentes
RUN_SEED=true ./emr-start

# Stack completo desde cero (DB + migrate + seed + servidores)
START_DB=true RUN_SEED=true ./emr-start

# Sin migraciones
RUN_MIGRATIONS=false ./emr-start

# Detener backend (:8000) y frontend (:3000)
./stop_servers.sh

# Diagnóstico (solo lectura)
./diagnose.sh
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `START_DB` | `false` | `docker compose up -d db` (solo Postgres, no el backend en Docker) |
| `RUN_MIGRATIONS` | `true` | `manage.py migrate --noinput` |
| `RUN_SEED` | `false` | `manage.py seed_data` (idempotente; **no** `poblar_db`) |

## Usuarios demo (`RUN_SEED=true`)

Creados por `core/management/commands/seed_data.py`:

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin123` | superuser |
| `medico1` | `medico123` | médico |
| `paciente1` | `paciente123` | paciente |
| `laboratorio1` | `laboratorio123` | laboratorio (LIMS) |

## URLs

- Frontend: http://localhost:3000
- API / Django: http://localhost:8000
- Admin: http://localhost:8000/admin/

## Logs

- `logs/backend.log`
- `logs/frontend.log`

## Seguridad

- Solo para **desarrollo local**.
- No apuntar a bases con **datos reales** sin backup.
- `RUN_SEED` no se ejecuta salvo que lo actives explícitamente.
- No se invocan comandos destructivos (`poblar_db`, etc.).

## Scripts locales (no versionados)

`start_servers.sh` y `setup_node.sh` en la raíz pueden existir en tu máquina con rutas personales; el flujo portable del repo es **`./emr-start`**. Si Node no está en PATH, instalá Node o cargá nvm — `diagnose.sh` indica qué falta.
