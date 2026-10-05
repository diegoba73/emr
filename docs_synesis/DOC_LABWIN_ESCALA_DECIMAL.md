# LabWin Firebird — escala decimal y rectificación

## Problema

LabWin guardaba en Firebird el valor “crudo” (`RESULT_FLD` como dígitos enteros).  
La presentación usaba `RESULTS.DECIMALES_FLD` (y a veces `FACTOR_FLD` en HEM).  
Si se importó el crudo a SYNESIS, un `5` puede ser clínicamente `0.5` o `50`.

## Motor

- Algoritmo: `laboratorio/labwin_firebird_scale.py`
- Imports Firebird nuevos ya escalan antes de mapear a LIMS.
- Alcance audit/rectify: `laboratorio/labwin_firebird_scope.py`

## Corte de escritura (obligatorio)

**Solo protocolos con `FECHA_FLD` ≤ 2026-09-29** pueden corregirse en BD.  
Fecha ≥ 2026-09-30: **nunca** se escribe (`skipped_after_until`).

Default de `--until`: `2026-09-29`.

## Comandos (dry-run primero)

Requiere export CSV: `DETERS.csv`, `PACIENTES.csv`, `RESULTS.csv`.

```bash
# Solo conteos (sin PHI)
python manage.py audit_labwin_firebird_scale /ruta/DATOS \
  --until 2026-09-29 \
  --all-firebird-overlap
# o delta R2:
python manage.py audit_labwin_firebird_scale /ruta/DATOS \
  --until 2026-09-29 \
  --only-r2-delta

# Dry-run de reparación (default: no escribe)
python manage.py rectify_labwin_firebird_scale /ruta/DATOS \
  --until 2026-09-29 \
  --all-firebird-overlap
```

Para órdenes `FINALIZADO` típicas de LabWin hace falta `--include-finalized` en el apply (y en el dry-run para ver `fixable`).

## Apply (solo con OK explícito del operador)

1. Backup Postgres.
2. Revisar conteos: `scale_error`, `fixable`, `skipped_after_until`.
3. Confirmar en chat: hacer / no hacer / solo no-finalizados.
4. Entonces:

```bash
python manage.py rectify_labwin_firebird_scale /ruta/DATOS \
  --until 2026-09-29 \
  --all-firebird-overlap \
  --include-finalized \
  --apply
```

Sin `--apply` no hay escrituras.

## Analítica (lectura)

UI LIMS: `/laboratorio/analytics` → `GET /api/lab/analytics/analitos/`  
Agregados sin PHI; default `hasta=2026-09-29`. No escribe resultados.
