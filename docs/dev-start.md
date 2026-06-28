# Arranque local EMR + LIMS (desarrollo)

`docs_synesis/` documenta el sistema en producción/diseño. Para trabajo con IA (SYNESIS, Cursor, Codex), ver `docs_synesis/DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md`. Este archivo describe **cómo levantar el stack en tu máquina** para probar con distintos usuarios.

## Requisitos

- Python virtualenv en `emr_env/` (raíz del repo)
- Node.js y `npm` en `PATH` (sin rutas absolutas; nvm u otro gestor es válido), **solo si** vas a levantar cliente en `frontend/`
- PostgreSQL en `:5432` (instalación local **o** contenedor Docker)

### Frontend local (contrastar con SoT)

Según **`docs_synesis/DOC_FRONTEND.md`**, una SPA React/Vue **no está confirmada como aplicación versionada** en este repositorio. Si existe la carpeta `frontend/` en tu checkout, tratala como **artefacto local o rama no alineada** hasta validar contra `DOC_FRONTEND.md` y el diff actual (`git status`, `package.json`, `frontend/src/`).

- Antes de `cd frontend && npm install` o asumir http://localhost:3000 como UI de producción: leer `DOC_FRONTEND.md`.
- Backend solo (API en :8000): omitir Node y `frontend/`.
- Si el frontend real está en **otro repo o rama**, indicarlo en tareas SYNESIS/Cursor (ver `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md`).

## Comandos

```bash
# Backend (+ frontend en :3000 solo si existe y está alineado con DOC_FRONTEND.md)
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
| `paciente1` | `paciente123` | paciente (Paciente Demo Uno) |
| `laboratorio1` | `laboratorio123` | laboratorio (LIMS) |
| `enfermeria1` | `enfermeria123` | enfermería |
| `secretaria1` | `secretaria123` | secretaría |

### Datos sintéticos QA (`seed_data`, idempotente)

Solo desarrollo/staging. **No usar datos reales.** Reejecutar: `python manage.py seed_data`.

| Artefacto | Clave estable | Uso |
|-----------|---------------|-----|
| Paciente Demo Uno | usuario `paciente1` | Portal paciente / turno LIMS |
| Paciente Demo Ajeno | DNI `QA-DEMO-AJENO-01` | Aislamiento 404/bloqueo |
| Turno demo | motivo `QA DEMO TURNO MEDICO1-PACIENTE1` | medico1 / paciente1 / agenda |
| Atención demo | vinculada al turno QA | smoke atenciones |
| Orden LIMS | `LAB-DEMO-QA-00001` | laboratorio1 / pantallas LIMS |
| Muestra LIMS | `MUE-DEMO-QA-00001` | trazabilidad demo |
| Resultado LIMS | Glucosa, valor demo no clínico | sin validar |

## URLs

- Frontend (solo si levantaste cliente local y `DOC_FRONTEND.md` lo confirma en tu tree): http://localhost:3000
- API / Django: http://localhost:8000
- Admin: http://localhost:8000/admin/

## Logs

- `logs/backend.log`
- `logs/frontend.log` (solo si `./emr-start` levantó cliente en `frontend/`)

## Seguridad

- Solo para **desarrollo local**.
- No apuntar a bases con **datos reales** sin backup.
- `RUN_SEED` no se ejecuta salvo que lo actives explícitamente.
- No se invocan comandos destructivos (`poblar_db`, etc.).

## Scripts locales (no versionados)

`start_servers.sh` y `setup_node.sh` en la raíz pueden existir en tu máquina con rutas personales; el flujo portable del repo es **`./emr-start`**. Si Node no está en PATH, instalá Node o cargá nvm — `diagnose.sh` indica qué falta.
