# Catálogos microbiológicos LabWin (ANTIB / BACTE / NEMOTEC / NEMOESPE)

## Propósito

Importar de forma **idempotente** los catálogos de referencia de LabWin hacia SYNESIS,
sin mezclar espacios de códigos (p. ej. `PSA` en BACTE ≠ `PSA` en NEMOTEC) y sin
pisar ediciones manuales del laboratorio.

## Fuentes

Exportación LabWin (CSV UTF-8, ver `LEEME.txt` del export):

- `ANTIB.csv` → `Antibiotico` (`origen=LABWIN_ANTIB`)
- `BACTE.csv` → `Microorganismo` (`origen=LABWIN_BACTE`)
- `NEMOTEC.csv` → `FraseRapidaMicrobiologia` (`origen=LABWIN_NEMOTEC`)
- `NEMOESPE.csv` → `FraseRapidaAsociacionAnalisis` (análisis LabWin + posición + nemotécnico)

Fixtures mínimos (solo tests/dev): `laboratorio/fixtures/labwin_micro_catalog_minimo/`.

## Comando

```bash
docker exec emr_backend python manage.py migrate laboratorio --noinput

# Dry-run / import con fixtures
docker exec emr_backend python manage.py import_labwin_micro_catalogos --fixtures --dry-run
docker exec emr_backend python manage.py import_labwin_micro_catalogos --fixtures
```

La ruta Windows/WSL (`G:\…` o `/mnt/g/…`) **no** existe dentro de `emr_backend`.
Copiá el export al repo y usá `/app/...`:

```bash
mkdir -p data/labwin_export
cp -a "/mnt/g/Mi unidad/laboratorio_ICPL/BD_labwin/Exportaciones_LabWin/Exportaciones_LabWin/20260919_124515_721148/." \
  data/labwin_export/

docker exec emr_backend python manage.py import_labwin_micro_catalogos \
  /app/data/labwin_export --dry-run
# Tras revisión + respaldo BD (solo desarrollo):
docker exec emr_backend python manage.py import_labwin_micro_catalogos /app/data/labwin_export
```

Cada corrida registra un `LabwinMicroCatalogImportBatch` (en dry-run se hace rollback
de los datos de catálogo con `transaction.set_rollback(True)`).

## Reglas de corrección

Ver `laboratorio/labwin_micro_catalog_corrections.py` y el reporte
`docs_synesis/reportes/labwin_micro_catalog_revision.md`.

Resumen:

| Código | Catálogo | Acción |
|--------|----------|--------|
| AS | ANTIB | Ortografía → Ampicilina/sulbactam |
| TS | ANTIB | Ortografía → Trimetoprima/sulfametoxazol |
| TTT | ANTIB | Inactivo (prueba) |
| NI, TA | ANTIB | Pendiente revisión |
| ENTC | NEMOTEC | Ortografía → Enterococcus faecalis (no BACTE) |
| CONT, col, stha, KLEBBLEE | NEMOTEC | Categoría FENOTIPO |
| gr1–gr5, uf+ | NEMOTEC | UMBRAL pendiente revisión |

## API

- `GET/POST/PATCH /api/lab/microbiologia/frases-rapidas/`
- `GET/POST/PATCH /api/lab/microbiologia/frases-rapidas-asociaciones/`
- Alias bajo `/api/laboratorio/microbiologia/...`

Un `PATCH` de microorganismo, antibiótico o frase marca `editado_manualmente=True`
para que reimportaciones no pisen el nombre.

## Resultado de antibiótico

Campos opcionales: `unidad_halo`, `unidad_mic`, `metodo`, `estandar_version`
(además de `halo_mm`, `mic`, `interpretacion`).

## Política

- No fusionar códigos entre catálogos distintos.
- No inventar especies a partir de hallazgos genéricos.
- No importar a producción sin dry-run + revisión profesional del reporte.
