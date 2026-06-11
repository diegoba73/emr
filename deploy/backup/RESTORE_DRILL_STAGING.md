# PROD-5-A — Restore drill seguro en staging

Procedimiento operativo para **validar recuperabilidad** de SYNESIS EMR/LIMS en un entorno **staging/temporal aislado**. No ejecutar contra producción.

## Objetivo

Confirmar que los backups de PROD-5 permiten:

- Restaurar PostgreSQL en una base staging explícita.
- Restaurar media clínica en ruta privada de staging.
- Verificar checksums, conteos agregados y `manage.py check`.
- Mantener `/media/` bloqueado por Nginx (PROD-4).

## Prohibiciones

- **No** restaurar contra la base productiva activa.
- **No** usar host/puerto/credenciales de producción como destino del drill.
- **No** commitear backups, dumps, tarballs ni evidencia con PHI.
- **No** ejecutar `dropdb`, `pg_restore --clean` ni `rm -rf` sobre rutas productivas.
- Preferir datos **anonimizados** o entorno autorizado si el backup contiene PHI.

## Variables obligatorias (drill)

| Variable | Descripción |
|----------|-------------|
| `CONFIRM_RESTORE=true` | Confirmación explícita antes de `restore_postgres.example.sh` |
| `RESTORE_TARGET_DB` | Nombre de base **staging** (p. ej. `synesis_staging_drill`) — **no** producción |
| `BACKUP_FILE` | Ruta al `.dump` usado (fuera del repo) |
| `MEDIA_RESTORE_DIR` | Directorio privado de staging para media (p. ej. `/var/staging/synesis/media`) |
| `PGHOST`, `PGPORT`, `PGUSER` | Conexión al PostgreSQL **de staging** |
| `PGPASSWORD` | Vía entorno; **no imprimir** |

Validar manualmente antes de continuar:

- `PGHOST` / `PGPORT` apuntan al servidor **staging**, no producción.
- `RESTORE_TARGET_DB` ≠ nombre real de la DB productiva en su entorno.
- El script bloquea `synesis_db` por defecto; no confiar solo en eso si producción usa otro nombre.

## Checklist pre-drill

- [ ] Entorno staging aislado (VM/contenedor/red separada).
- [ ] Base destino creada y vacía (operador; fuera de alcance de scripts del repo).
- [ ] `BACKUP_DIR` y artefactos fuera del repositorio git.
- [ ] Checksum del backup disponible (`.sha256`).
- [ ] Tarball media alineado en timestamp con backup DB.
- [ ] Operador responsable identificado.
- [ ] Ventana de mantenimiento acordada (staging).

## Procedimiento paso a paso

### 1. Verificar checksum del backup DB

```bash
sha256sum -c "${BACKUP_FILE}.sha256"
```

Si falla, **no restaurar**. Obtener backup íntegro.

### 2. Verificar checksum del backup media (si aplica)

```bash
sha256sum -c "${MEDIA_ARCHIVE}.sha256"
```

### 3. Restore PostgreSQL (solo staging)

```bash
export CONFIRM_RESTORE=true
export RESTORE_TARGET_DB=synesis_staging_drill   # ejemplo — usar nombre staging real
export BACKUP_FILE=/var/backups/synesis/postgres_YYYYMMDD.dump
export PGHOST=staging-db.example.internal
export PGPORT=5432
export PGUSER=synesis_restore
# PGPASSWORD vía entorno

./deploy/backup/restore_postgres.example.sh
```

### 4. Restore media en ruta privada

```bash
mkdir -p "${MEDIA_RESTORE_DIR}"
tar -xzf "${MEDIA_ARCHIVE}" -C "$(dirname "${MEDIA_RESTORE_DIR}")"
# Ajustar si el tarball incluye subdirectorio; media debe quedar privada, no bajo docroot Nginx
```

Configurar backend staging con `MEDIA_ROOT=${MEDIA_RESTORE_DIR}` (variable de entorno; no servir por `/media/`).

### 5. Verificación post-restore (no destructiva)

```bash
export CONFIRM_DRILL_VERIFY=true
export RESTORE_TARGET_DB=synesis_staging_drill
export BACKUP_FILE=/var/backups/synesis/postgres_YYYYMMDD.dump
export MEDIA_RESTORE_DIR=/var/staging/synesis/media
export PGHOST=staging-db.example.internal
export PGPORT=5432
export PGUSER=synesis_restore
export DJANGO_SETTINGS_MODULE=synesis.settings
# DB_* / DJANGO_* apuntando solo a staging

./deploy/backup/verify_restore.example.sh
```

### 6. Conteos agregados permitidos (sin PHI)

Solo `COUNT(*)` — no listar filas ni datos clínicos:

```sql
SELECT COUNT(*) FROM pacientes_paciente;
SELECT COUNT(*) FROM laboratorio_solicitudexamen;
SELECT COUNT(*) FROM laboratorio_resultadoexamen;
SELECT COUNT(*) FROM turnos_atencion;
SELECT COUNT(*) FROM emr_documento;
```

Registrar **solo números** en evidencia operativa (fuera del repo).

### 7. Verificar aplicación

- `./manage.py check` contra DB staging.
- `GET /api/health/` en backend staging.
- Smoke test de login (usuario de prueba staging).
- Descarga autenticada de adjunto (PROD-4-A) si hay archivo de prueba en staging — **sin** usar `/media/` público.

### 8. Verificar `/media/` bloqueado (Nginx prod template)

La plantilla `deploy/nginx/nginx.prod.example.conf` debe mantener `location /media/ { deny all; }`. El drill **no** expone media por Nginx.

```bash
docker run --rm \
  --add-host backend:127.0.0.1 \
  -v "$(pwd)/deploy/nginx/nginx.prod.example.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine nginx -t
```

### 9. Registro de evidencia (sin PHI)

Documentar **fuera del repositorio**:

| Campo | Ejemplo |
|-------|---------|
| Fecha | 2026-06-11 |
| Entorno | staging-drill-01 |
| Backup usado | `postgres_20260610.dump` (checksum OK) |
| Media usada | `media_20260610.tar.gz` (checksum OK) |
| `RESTORE_TARGET_DB` | `synesis_staging_drill` |
| Resultado restore DB | OK / FAIL |
| Resultado media | OK / FAIL |
| `manage.py check` | OK / FAIL |
| Conteos agregados | solo enteros |
| `/media/` Nginx | bloqueado |
| Operador | identificador interno |
| Incidencias | texto sin datos clínicos |

**No commitear** este registro si contiene PHI.

### 10. Cleanup seguro

- Eliminar o cifrar artefactos temporales del drill según política del operador.
- Revocar credenciales temporales de staging.
- No dejar backups en el working tree del repo.

## Referencias

- `deploy/backup/README.md` — plantillas PROD-5
- `deploy/backup/restore_postgres.example.sh`
- `deploy/backup/verify_restore.example.sh`
- `docs_synesis/PROD_RUNTIME.md` — PROD-4 media privada

## Fuera de alcance PROD-5-A

- Ejecución automática del drill en CI.
- Restore en producción.
- S3/MinIO, cifrado implementado en scripts, scheduling externo.
- Anonimización automatizada de datos.
