#!/usr/bin/env bash
# Ticket B apply pipeline — SOLO Docker/dev. No producción. No QC.
set -euo pipefail
cd "$(dirname "$0")/.."
REPORT="docs/ticket-b-apply-dev-report.txt"
: > "$REPORT"
log() { echo "$@" | tee -a "$REPORT"; }

log "=== $(date -u -Iseconds) Ticket B apply Docker/dev ==="

log "-- showmigrations --"
docker compose exec -T backend python manage.py showmigrations laboratorio | grep -E '0049|0050' | tee -a "$REPORT"

log "-- unit tests apply path --"
docker compose exec -T backend python manage.py test laboratorio.tests.test_cargar_reactivos_matriz --keepdb -v1 | tee -a "$REPORT"

log "-- dry-run --"
docker compose exec -T backend python manage.py cargar_reactivos_equipo_matriz | tee -a "$REPORT"

mkdir -p "$HOME/backups_synesis"
TS=$(date -u +%Y%m%d_%H%M%S)
BACKUP="$HOME/backups_synesis/synesis_db_ticketb_${TS}.dump"
log "-- backup -> $BACKUP --"
docker compose exec -T db pg_dump -U postgres -Fc synesis_db > "$BACKUP"
ls -la "$BACKUP" | tee -a "$REPORT"

log "-- BEFORE --"
docker compose exec -T backend python manage.py shell <<'PY' | tee -a "$REPORT"
from laboratorio.models_inventario import InsumoLab, MovimientoStock, ConsumoInsumoExamen, LoteInsumo
print("reactivos", InsumoLab.objects.filter(tipo="REACTIVO").count())
print("r_star", InsumoLab.objects.filter(codigo__startswith="R-").count())
print("mov", MovimientoStock.objects.count())
print("consumos", ConsumoInsumoExamen.objects.count())
print("lotes", LoteInsumo.objects.count())
print("cre_glu", list(InsumoLab.objects.filter(codigo__in=["CRE","GLU"]).values_list("codigo","proveedor","ref_comercial")))
PY

log "-- APPLY 1 --"
docker compose exec -T backend python manage.py cargar_reactivos_equipo_matriz --apply | tee -a "$REPORT"
log "-- APPLY 2 (idempotencia) --"
docker compose exec -T backend python manage.py cargar_reactivos_equipo_matriz --apply | tee -a "$REPORT"

log "-- AFTER / VERIFY --"
docker compose exec -T backend python manage.py shell <<'PY' | tee -a "$REPORT"
from laboratorio.models_inventario import InsumoLab, LoteInsumo, MovimientoStock, ConsumoInsumoExamen
from laboratorio.reactivos_matriz_catalogo import REACTIVOS_CATALOGO_CONFIRMADOS
skus={r["codigo"] for r in REACTIVOS_CATALOGO_CONFIRMADOS}
qs=list(InsumoLab.objects.filter(codigo__in=skus))
print("created", len(qs))
print("stock0", all(i.stock_actual==0 for i in qs))
print("lotes_r", LoteInsumo.objects.filter(insumo__codigo__in=skus).count())
print("ferr", InsumoLab.objects.filter(codigo__icontains="FERR").count())
print("cre_glu", list(InsumoLab.objects.filter(codigo__in=["CRE","GLU"]).values_list("codigo","proveedor","ref_comercial")))
print("mov", MovimientoStock.objects.count())
print("consumos", ConsumoInsumoExamen.objects.count())
print("reactivos_tot", InsumoLab.objects.filter(tipo="REACTIVO").count())
print("dup_skus", len(qs) != len({i.codigo for i in qs}))
PY

log "-- regressions inventario --"
docker compose exec -T backend python manage.py test laboratorio.tests.test_inventario_reactivos laboratorio.tests.test_cargar_reactivos_matriz --keepdb -v1 | tee -a "$REPORT"
log "-- regressions QC --"
docker compose exec -T backend python manage.py test laboratorio.tests.test_qc_gate laboratorio.tests.test_qc_hibrido --keepdb -v1 | tee -a "$REPORT"

log "-- git --"
git status -sb | tee -a "$REPORT"
git diff --stat HEAD | head -80 | tee -a "$REPORT"

log "DONE report=$REPORT backup=$BACKUP"
