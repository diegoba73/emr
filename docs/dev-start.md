# Arranque local EMR + LIMS (desarrollo)

## Modo recomendado: todo en Docker

Misma arquitectura que producción (Postgres + Gunicorn/runserver en contenedor + Nginx en prod).
Una sola base de datos: contenedor `emr_postgres` → `synesis_db`.

Requisito: **Docker Desktop** (o Docker Engine) corriendo.

### Primera vez

```bash
cp .env.example .env
./emrctl up --seed          # db + backend + datos demo + catálogo LIMS
./emrctl up --full --seed   # incluye frontend React en Docker
```

### Cada día

```bash
./emrctl up                 # db + backend
./emrctl up --full            # db + backend + frontend
```

### URLs

- Frontend: http://localhost:3000 (con `--full`, o `cd frontend && npm start`)
- API: http://localhost:8000
- Admin: http://localhost:8000/admin/

## Recuperar datos desde backup

Si tenés un dump en `~/backups_synesis/` (p. ej. del 22/jun/2026):

```bash
bash scripts/restore_docker_db.sh ~/backups_synesis/synesis_db_20260622_233218.dump
./emrctl up
./emrctl seed               # repone catálogo LIMS completo si hace falta
```

El script hace backup de seguridad de la BD actual antes de restaurar.

## Variables de `.env`

Para desarrollo con Docker, el backend en contenedor usa `DB_HOST=db` (definido en `docker-compose.yml`).
Si corrés comandos `manage.py` **desde tu terminal** contra la misma BD:

```env
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=synesis_db
DB_PORT=5432
```

**No uses** `synesis_user` ni Postgres nativo en WSL.

## Comandos útiles

```bash
./emrctl status
./emrctl seed                 # datos demo + catálogo LIMS + salas estudio (idempotente)
./emrctl logs backend
./emrctl down                 # apaga todo (datos persisten en volumen)
bash scripts/backup_postgres_local.sh   # backup manual
```

## Usuarios demo

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin123` | superuser |
| `medico1` | `medico123` | médico |
| `secretaria1` | `secretaria123` | secretaría |
| `laboratorio1` | `laboratorio123` | laboratorio |

Orden LIMS demo: `LAB-DEMO-QA-00001`

## Permisos por rol (EMR)

Matriz acordada para desarrollo y QA manual. El **backend** es fuente de verdad; el frontend refleja la misma lógica para habilitar/deshabilitar UI.

| Rol | Ver | Editar |
|-----|-----|--------|
| **Médico** | Turnos asignados a él (consulta propia + estudios de sus pacientes vinculados) | Todo en esos turnos (campos, confirmar, cancelar, reprogramar) |
| **Paciente** | Sus turnos (consulta y estudio) | Crear y editar hasta que el turno quede `REALIZADO`, `CANCELADO` o tenga atención clínica iniciada |
| **Secretaría** | Pacientes, turnos, estudios complementarios, laboratorio/LIMS, catálogos clínicos | Solo **pacientes** y **turnos**; estudios, laboratorio y catálogos son **solo lectura** |

### Detalle por módulo

- **Turnos** (`/turnos`): médico filtrado por propiedad; paciente solo los propios; secretaría agenda global con edición.
- **Estudios complementarios**: secretaría lista y asigna turnos de sala (`agendar-turno` / `asignar-turno`) pero no crea ni modifica fichas de estudio.
- **Laboratorio / LIMS** (`/solicitudes`, `/laboratorio/*`): secretaría navega y consulta; operaciones técnicas solo `admin` y `laboratorio`.
- **Catálogos clínicos** (CIE-10, medicamentos, etc.): secretaría lectura; edición admin/médico.

### Tests automatizados

```bash
# Permisos turnos estudio + secretaría estudios
python manage.py test turnos.tests.test_medico_estudio_turnos

# Permisos solicitudes (secretaría solo lectura)
python manage.py test solicitudes.tests.test_permissions_api

# Frontend (vitest/jest según proyecto)
cd frontend && npm test -- turnoPermissions.test.ts
```

Archivos clave: `turnos/access.py`, `turnos/turno_estado.py`, `frontend/src/utils/turnoPermissions.ts`, `frontend/src/utils/limsAccess.ts`, `estudios/access.py`.

## Modo híbrido (opcional)

Solo si necesitás depurar con `runserver` en el IDE:

```bash
./emrctl up --hybrid
source emr_env/bin/activate && python manage.py runserver 8000
```

**No** corras `runserver` si `emr_backend` ya está activo (puerto 8000 ocupado).

## Datos

- Persisten en volumen Docker `emr_postgres_data`.
- **No** ejecutes `docker compose down -v` salvo que quieras borrar todo.
