# PROD-5 — Backups y restore (plantillas)

Plantillas versionadas para backup/restore de **PostgreSQL** y **media clínica privada**. No contienen secretos ni rutas productivas reales.

## Alcance

| Componente | Script | Obligatorio para recuperación completa |
|------------|--------|--------------------------------------|
| PostgreSQL | `backup_postgres.example.sh` | Sí |
| Media clínica (`MEDIA_ROOT`) | `backup_media.example.sh` | Sí (adjuntos, documentos, archivos en disco) |

La API sirve media vía endpoints autenticados (PROD-4); el backup de disco complementa la base de datos.

## Variables (operador)

### Backup PostgreSQL

| Variable | Descripción |
|----------|-------------|
| `BACKUP_DIR` | Directorio de salida **fuera del repo** (p. ej. `/var/backups/synesis`) |
| `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE` | Conexión PostgreSQL |
| `PGPASSWORD` | Opcional vía entorno; **no imprimir** |

### Backup media

| Variable | Descripción |
|----------|-------------|
| `BACKUP_DIR` | Idem |
| `MEDIA_ROOT` | Ruta al volumen media del backend (p. ej. `/app/media` en contenedor) |

### Restore PostgreSQL (solo staging / drill)

| Variable | Descripción |
|----------|-------------|
| `CONFIRM_RESTORE=true` | **Obligatorio** — confirmación explícita |
| `RESTORE_TARGET_DB` | Base destino (staging vacía o de prueba) |
| `BACKUP_FILE` | Ruta al `.dump` |
| `PGHOST`, `PGPORT`, `PGUSER` | Conexión |
| `ALLOW_RESTORE_PRODUCTION_NAME=true` | Solo si el operador asume riesgo sobre nombre `synesis_db` (ejemplo compose) |

**No ejecutar restore sobre la base productiva activa.** Probar siempre en staging aislado primero.

**Protección de nombres productivos:** el script bloquea `synesis_db` por defecto (nombre del compose example). El operador **debe** usar `RESTORE_TARGET_DB` con un nombre de staging/drill distinto del nombre real de producción en su entorno (p. ej. `synesis_staging_restore`). Si el nombre productivo difiere de `synesis_db`, no confiar solo en el bloqueo del script: validar host/puerto, usar credenciales de staging y políticas de firewall antes de cualquier restore.

## Periodicidad sugerida (operador)

| Tipo | Frecuencia sugerida | Retención sugerida |
|------|---------------------|-------------------|
| PostgreSQL | Diaria (ventana de bajo tráfico) | 7–30 días local + copia offsite |
| Media | Diaria o semanal según volumen | Alineada a DB (mismo timestamp de corrida) |

## RPO / RTO (recomendación operativa, no garantía)

- **RPO sugerido:** hasta 24 h si backup diario; menor si el operador aumenta frecuencia.
- **RTO sugerido:** depende de tamaño de DB/media, hardware y drill; planificar horas, no minutos, hasta validar en staging.

## Restore drill (staging)

Procedimiento completo: **`RESTORE_DRILL_STAGING.md`**. Verificación post-restore no destructiva: **`verify_restore.example.sh`** (`CONFIRM_DRILL_VERIFY=true`).

Resumen:
2. Restaurar último backup PostgreSQL con `restore_postgres.example.sh`.
3. Extraer tarball media al `MEDIA_ROOT` de staging (`tar -xzf …`).
4. Verificar checksums (`.sha256`).
5. Smoke test: healthcheck, login, descarga autenticada de un adjunto de prueba (sin PHI real en repo).
6. Documentar tiempo y incidencias.

## Seguridad

- **No commitear** archivos `.dump`, `.tar.gz`, `.sha256` ni directorios `backups/` / `deploy/backup/output/`.
- Cifrado en reposo y almacenamiento offsite: responsabilidad del operador (S3/MinIO fuera de alcance PROD-5).
- Control de acceso a backups: solo roles operativos autorizados.
- Los scripts no imprimen passwords ni `DATABASE_URL` completa.
- **Artefacto local legacy:** `backup_pendrive.sql` en raíz del repo puede existir en disco; está listado en `.gitignore` y no debe commitearse. Si contiene datos sensibles, mover fuera del repositorio.

## Sintaxis (validación local)

```bash
bash -n deploy/backup/backup_postgres.example.sh
bash -n deploy/backup/backup_media.example.sh
bash -n deploy/backup/restore_postgres.example.sh
```

## Fuera de alcance PROD-5

- Jobs automáticos en compose (no hay cron en `docker-compose.prod.example.yml`).
- S3/MinIO, TLS/ACME, WAF, monitoreo externo.
- Restore destructivo automatizado (`dropdb`, `rm -rf` sobre producción).
