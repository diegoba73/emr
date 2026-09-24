#!/usr/bin/env bash
# Verificacion local de escala LabWin (sin tocar prod).
set -euo pipefail
cd /home/diego/proyectos/emr

echo "== smoke =="
python3 - <<'PY'
from decimal import Decimal
from laboratorio.labwin_firebird_scale import ResultMeta, scale_digit_token, interpret_atomic
print(scale_digit_token("152", ResultMeta("URE",1,1,1,"1",1,Decimal("1"))).valor_clinico)
print(scale_digit_token("1023", ResultMeta("CRE",1,1,1,"1",2,Decimal("1"))).valor_clinico)
print(scale_digit_token("152", ResultMeta("GLU",1,1,1,"1",0,Decimal("1"))).valor_clinico)
print(interpret_atomic("-11", ResultMeta("X",1,1,1,"1",1,Decimal("1"))).valor_clinico)
PY

echo "== pytest =="
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: \
  python3 -m pytest laboratorio/tests/test_labwin_firebird_scale.py -q

DATOS="/mnt/c/Users/diego/Downloads/SYNESIS_R2_Firebird_para_Cursor/DATOS"
if [[ -d "$DATOS" ]]; then
  echo "== offline DETERS counts =="
  python3 - <<PY
from pathlib import Path
from collections import Counter
import csv
from laboratorio.labwin_firebird_scale import load_results_catalog, interpret_result_fld
DATOS = Path("$DATOS")
cat = load_results_catalog(DATOS / "RESULTS.csv")
c = Counter()
with (DATOS / "DETERS.csv").open(encoding="utf-8-sig", newline="") as fh:
    for row in csv.DictReader(fh):
        if (row.get("PRV_DELETEDRECORD_FLD") or "").strip() not in ("", "0", "False", "false"):
            continue
        abrev = (row.get("ABREV_FLD") or "").strip().strip('"')
        raw = (row.get("RESULT_FLD") or "").strip().strip('"')
        if not raw:
            c["empty"] += 1
            continue
        for o in interpret_result_fld(abrev, raw, cat):
            c[o.status] += 1
            if o.status == "ok" and o.valor_clinico and o.original != o.valor_clinico:
                tok = o.original
                if tok.isdigit() or (tok[:1] in "<>" and tok.lstrip("<>").isdigit()):
                    c["would_change_vs_raw"] += 1
            if o.status == "ok" and o.valor_clinico == o.original:
                c["ok_identity"] += 1
print(dict(c))
print("catalog", len(cat))
PY
fi

echo "DONE — para auditar PG local (solo conteos):"
echo "  python3 manage.py audit_labwin_firebird_scale \"$DATOS\" --only-r2-delta"
