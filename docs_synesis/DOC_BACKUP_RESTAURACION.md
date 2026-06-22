# DOC_BACKUP_RESTAURACION — Backup y restauración operativa SYNESIS

**Fecha:** 21 de junio de 2026  
**Alcance:** instalación local / controlada (desarrollo, staging, drill).  
**No sustituye:** runbooks productivos PROD-5 en `deploy/backup/` y `PROD_RUNTIME.md`.

---

## Propósito

Responder de forma reproducible y segura:

- cómo respaldar PostgreSQL;
- cómo respaldar `media/` (archivos clínicos en disco);
- cómo resguardar `.env` **fuera de Git**;
- cómo restaurar SYNESIS desde cero o en base de prueba;
- cómo verificar post-restore;
- qué **nunca** debe subirse al repositorio.

**Regla principal:** GitHub = código, documentación segura y scripts reproducibles.  
Backup seguro **fuera de Git** = DB real, media, `.env`, secretos y dumps.

---

## Qué cubre

| Componente | Obligatorio para recuperación completa | Herramienta local |
|------------|--------------------------------------|-------------------|
| PostgreSQL (`synesis_db` u otro `DB_NAME`) | **Sí** | `scripts/backup_postgres_local.sh` |
| Media (`MEDIA_ROOT` → `media/` en repo) | **Sí** si hay adjuntos/documentos | `tar` (ver sección Media) |
| `.env` (secretos, credenciales) | **Sí** | copia manual fuera del repo |
| Código SYNESIS | Versionado en Git | `git clone` / checkout tag |

Referencias productivas (plantillas, no ejecutar ciegamente en prod): `deploy/backup/backup_postgres.example.sh`, `deploy/backup/backup_media.example.sh`, `deploy/backup/restore_postgres.example.sh`, `deploy/backup/RESTORE_DRILL_STAGING.md`.

---

## Qué no cubre

- Producción clínica abierta ni autorización institucional de datos reales.
- Cifrado offsite, S3/MinIO, cron automatizado en servidor (responsabilidad operador).
- Suite PostgreSQL completa en CI.
- Importación parcial de tablas (puede romper trazabilidad).
- Rotación de secretos filtrados (ver `PROD_SECRET_ROTATION_RUNBOOK.md`).

---

## Componentes a respaldar

### 1. PostgreSQL

Contiene: pacientes, usuarios, turnos, historias, LIMS (solicitudes, muestras, resultados, microbiología), **tablas de auditoría**, relaciones clínicas.

**Tratamiento:** PHI/PII — almacenar cifrado o en ubicación con acceso restringido.

Configuración Django (`synesis/settings.py`):

- `DB_ENGINE` (default `django.db.backends.postgresql`)
- `DB_NAME` (default `synesis_db`)
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` vía `.env`

### 2. Media / uploads

- `MEDIA_ROOT` = `<repo>/media` (local)
- `MEDIA_URL` = `/media/`
- Puede contener documentos médicos, adjuntos de turnos, archivos clínicos.

Si existe `uploads/` en algún despliegue, aplicar la misma política que `media/`.

### 3. Configuración `.env`

Plantilla segura versionada: **`.env.example`** (sin secretos reales).  
Copia operativa: **`.env`** — **nunca commitear**.

---

## Backup PostgreSQL (local)

### Prerrequisitos

```bash
pg_dump --version
psql --version
python3 manage.py check   # con venv activo si aplica
```

### Script recomendado (fuera del repo)

```bash
cd /home/diego/proyectos/emr
BACKUP_DIR="${HOME}/backups_synesis" DB_NAME="synesis_db" bash scripts/backup_postgres_local.sh
```

**Defaults editables:**

| Variable | Default |
|----------|---------|
| `DB_NAME` | `synesis_db` |
| `BACKUP_DIR` | `$HOME/backups_synesis` |
| `PGHOST` | `localhost` |
| `PGPORT` | `5432` |
| `PGUSER` | `postgres` |
| `PGPASSWORD` | solo entorno del operador; **no se imprime** |

**Salida:** `~/backups_synesis/synesis_db_YYYYMMDD_HHMMSS.dump` (+ `.sha256` si disponible).

### Comando manual equivalente

```bash
mkdir -p ~/backups_synesis
chmod 700 ~/backups_synesis
pg_dump -Fc -h localhost -U postgres -d synesis_db \
  -f ~/backups_synesis/synesis_db_$(date +%Y%m%d_%H%M%S).dump
```

El script rechaza `BACKUP_DIR` dentro del repositorio.

---

## Backup media / uploads

Solo si el directorio existe y tiene contenido:

```bash
BACKUP_DIR="${HOME}/backups_synesis"
MEDIA_ROOT="/home/diego/proyectos/emr/media"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
tar -czf "${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz" -C "$(dirname "${MEDIA_ROOT}")" "$(basename "${MEDIA_ROOT}")"
sha256sum "${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz" > "${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz.sha256"
```

Plantilla productiva: `deploy/backup/backup_media.example.sh`.

---

## Backup `.env`

```bash
cp .env ~/backups_synesis/env_$(date +%Y%m%d_%H%M%S).env
chmod 600 ~/backups_synesis/env_*.env
```

- No subir a Git, email ni chat.
- Rotar credenciales si hubo exposición.

---

## Restauración desde cero (nuevo entorno)

1. Clonar repositorio SYNESIS (código desde Git).
2. Crear venv e instalar `requirements.txt`.
3. Copiar `.env.example` → `.env` y configurar (o restaurar copia segura de `.env`).
4. Crear rol/base PostgreSQL vacía si es instalación nueva.
5. **Restaurar dump en base de prueba primero** (ver abajo).
6. Validar `python manage.py check` y smoke focal.
7. Extraer tarball `media_*.tar.gz` a `MEDIA_ROOT` si aplica.
8. Solo tras validación, repetir restore en base definitiva con confirmación explícita.

---

## Restauración en base de prueba (recomendado)

```bash
TARGET_DB="synesis_restore_test" \
  bash scripts/restore_postgres_local.sh ~/backups_synesis/synesis_db_YYYYMMDD_HHMMSS.dump
```

**Defaults del script:**

| Variable | Default |
|----------|---------|
| `TARGET_DB` | `synesis_restore_test` |
| `PROD_DB_NAME` | `synesis_db` (nombre bloqueado sin confirmación) |

**Restaurar sobre `synesis_db` (base real):** requiere:

```bash
CONFIRM_RESTORE_PROD=YES_I_UNDERSTAND TARGET_DB=synesis_db \
  bash scripts/restore_postgres_local.sh ~/backups_synesis/<archivo>.dump
```

El script **no ejecuta `dropdb`** por defecto. Si la base destino ya existe con datos, `pg_restore` puede fallar — usar base vacía o nombre distinto.

### Comandos manuales equivalentes (prueba)

```bash
createdb -h localhost -U postgres synesis_restore_test
pg_restore -h localhost -U postgres -d synesis_restore_test --no-owner --no-acl \
  ~/backups_synesis/<archivo>.dump
```

---

## Checklist post-restore

- [ ] `python manage.py check` → 0 issues
- [ ] Conexión a la base restaurada (`DB_NAME` correcto en `.env`)
- [ ] Login con usuario de prueba (sintético; sin PHI en logs)
- [ ] `GET /api/health/` responde
- [ ] Smoke pytest focal: `pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q`
- [ ] Descarga autenticada de adjunto de prueba (si media restaurada)
- [ ] Tablas de auditoría presentes y coherentes en timestamp
- [ ] Registrar en bitácora operativa: fecha, operador, archivo dump, base destino

---

## Preservación de auditoría y trazabilidad

Un restore **completo** de PostgreSQL preserva:

- `AuditEvent` y metadata asociada;
- usuarios y permisos;
- relaciones clínicas (paciente ↔ turno ↔ atención ↔ LIMS);
- órdenes, muestras, resultados, informes.

**Riesgos que rompen trazabilidad:**

- importar solo algunas tablas;
- ejecutar migraciones manuales fuera de orden;
- mezclar dump antiguo con media nueva (o viceversa);
- restaurar sobre base productiva sin backup previo.

---

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Dump en el repo | `.gitignore`; script bloquea `BACKUP_DIR` dentro del repo |
| Restore accidental en prod | `TARGET_DB` default de prueba; `CONFIRM_RESTORE_PROD` obligatorio |
| Filtración PHI por Git | nunca `git add` dumps, media, `.env` |
| Backup sin media | recuperación incompleta de documentos |
| Credenciales en logs | scripts no imprimen `PGPASSWORD` ni contenido de tablas |

---

## Plan de emergencia (resumen)

1. **Detener** escrituras si hay corrupción activa (modo mantenimiento).
2. **No** borrar la base dañada hasta tener backup verificado.
3. Restaurar último dump **en staging** (`synesis_restore_test`).
4. Validar checklist post-restore.
5. Ventana de mantenimiento → restore en base definitiva con confirmación.
6. Plan de reversión: conservar dump previo a la intervención.

---

## Comandos seguros

```bash
bash scripts/backup_postgres_local.sh
TARGET_DB=synesis_restore_test bash scripts/restore_postgres_local.sh ~/backups_synesis/<archivo>.dump
python manage.py check
bash -n scripts/backup_postgres_local.sh
bash -n scripts/restore_postgres_local.sh
```

---

## Comandos prohibidos o peligrosos

```bash
# NO — destruye base sin backup confirmado
dropdb synesis_db

# NO — restaurar prod sin confirmación
pg_restore -d synesis_db ...

# NO — versionar datos sensibles
git add *.dump .env media/

# NO — compartir dumps por canales inseguros
```

---

## Política: no subir datos sensibles a Git

**Nunca commitear:**

- `.env`, `.env.*` reales (salvo `!.env.example`, `!.env.production.example`)
- `*.sql`, `*.dump`, `*.backup`, `*.pgdump`
- `backups/`, `media/`, `uploads/` con contenido real
- tokens, claves privadas, certificados privados
- dumps PostgreSQL, exports CSV clínicos, documentos de pacientes

**GitHub** aloja código y documentación operativa segura.  
**Backups** viven en `~/backups_synesis` u otra ruta fuera del repo, con permisos restrictivos (`chmod 700`).

---

## Seguridad y confidencialidad

- Los backups PostgreSQL pueden contener **PHI/PII** (pacientes, resultados, informes, auditoría).
- Cifrar en reposo o almacenar en volumen con acceso mínimo.
- Restringir por usuario del sistema operativo.
- No enviar backups por email, chat ni issues de GitHub.
- Si se filtraron credenciales del `.env`, rotar `SECRET_KEY`, passwords DB y JWT según `PROD_SECRET_ROTATION_RUNBOOK.md`.

---

## Relación con documentación existente

| Documento | Contenido |
|-----------|-----------|
| `deploy/backup/README.md` | Plantillas PROD-5 (postgres + media + restore drill) |
| `deploy/backup/RESTORE_DRILL_STAGING.md` | Drill staging productivo |
| `.env.example` | Variables sin secretos reales |
| `DOC_TESTS.md` | Tests `test_prod_backup_config.py`, `test_prod_restore_drill_config.py` |
| `PROD_RUNTIME.md` | Runtime productivo y backups |

Este documento complementa PROD-5 con **flujo local explícito** en `scripts/backup_postgres_local.sh` y `scripts/restore_postgres_local.sh`.
