#!/usr/bin/env python
"""Read-only coverage check: SoT materiales-pedido vs DB.

Uso (local o prod, dentro del contenedor backend):

  python manage.py shell < scripts/check_materiales_pedido_coverage.py

O:

  python -c "exec(open('scripts/check_materiales_pedido_coverage.py').read())"
"""
from __future__ import annotations

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emr.settings")
if not django.apps.apps.ready:
    django.setup()

from laboratorio.materiales_pedido_catalogo import (  # noqa: E402
    CULTIVOS_MICRO_EXTRA,
    MATERIALES_PEDIDO,
    MUESTRAS_MICRO_EXTRA,
    grilla_codigos_material,
    todas_muestras_clinicas,
    todos_examenes_materiales,
)
from laboratorio.micro_catalogos_seed import (  # noqa: E402
    TIPOS_CULTIVO_MICRO_SEED,
    TIPOS_MUESTRA_MICRO_SEED,
)
from laboratorio.models import TipoExamen, TipoMuestra  # noqa: E402
from laboratorio.models_catalog import TipoContenedor  # noqa: E402
from laboratorio.models_microbiologia import (  # noqa: E402
    TipoCultivoMicrobiologia,
    TipoMuestraMicrobiologia,
)
from laboratorio.tubos_catalogo import FRASCO_ESTERIL  # noqa: E402

print("DB_HOST", os.environ.get("DB_HOST"), "DB_NAME", os.environ.get("DB_NAME"))
print("FRASCO_ESTERIL", TipoContenedor.objects.filter(codigo=FRASCO_ESTERIL, activo=True).exists())

missing_tm = sorted(
    c
    for c in todas_muestras_clinicas()
    if not TipoMuestra.objects.filter(codigo=c, activo=True).exists()
)
print("MISSING_TM_N", len(missing_tm))
if missing_tm:
    print("MISSING_TM", missing_tm)

want_ex = {e.codigo: e for e in todos_examenes_materiales()}
db_ex = {
    te.codigo: te
    for te in TipoExamen.objects.filter(codigo__in=want_ex).select_related(
        "tipo_muestra_requerida", "tipo_contenedor"
    )
}
missing_ex = sorted(set(want_ex) - set(db_ex))
print("MISSING_EX_N", len(missing_ex))
if missing_ex:
    print("MISSING_EX", missing_ex)

no_frasco = sorted(
    c
    for c, te in db_ex.items()
    if te.activo
    and (
        te.tipo_contenedor_id is None
        or getattr(te.tipo_contenedor, "codigo", None) != FRASCO_ESTERIL
    )
)
print("NO_FRASCO_N", len(no_frasco))
if no_frasco:
    print("NO_FRASCO", no_frasco)

want_c = {c for c, _, _ in TIPOS_CULTIVO_MICRO_SEED}
db_c = set(
    TipoCultivoMicrobiologia.objects.filter(codigo__in=want_c, activo=True).values_list(
        "codigo", flat=True
    )
)
missing_c = sorted(want_c - db_c)
print("MISSING_CULTIVOS_N", len(missing_c))
if missing_c:
    print("MISSING_CULTIVOS", missing_c)

want_m = {c for c, _, _ in TIPOS_MUESTRA_MICRO_SEED}
db_m = set(
    TipoMuestraMicrobiologia.objects.filter(codigo__in=want_m, activo=True).values_list(
        "codigo", flat=True
    )
)
missing_m = sorted(want_m - db_m)
print("MISSING_MUESTRAS_MICRO_N", len(missing_m))
if missing_m:
    print("MISSING_MUESTRAS_MICRO", missing_m)

unres_c = [
    f"{m.codigo}->{m.cultivo_micro}"
    for m in MATERIALES_PEDIDO
    if m.cultivo_micro
    and not TipoCultivoMicrobiologia.objects.filter(
        codigo=m.cultivo_micro, activo=True
    ).exists()
]
unres_m = [
    f"{m.codigo}->{m.muestra_micro}"
    for m in MATERIALES_PEDIDO
    if m.muestra_micro
    and not TipoMuestraMicrobiologia.objects.filter(
        codigo=m.muestra_micro, activo=True
    ).exists()
]
print("UNRESOLVABLE_CULTIVO", unres_c)
print("UNRESOLVABLE_MUESTRA_MICRO", unres_m)

empty = []
for mat in MATERIALES_PEDIDO:
    codes = grilla_codigos_material(mat)
    if not codes:
        continue
    n = TipoExamen.objects.filter(codigo__in=codes, activo=True).count()
    if n == 0:
        empty.append(mat.codigo)
print("EMPTY_CLINICAL_GRIDS", empty)

print(
    "SPOT",
    {
        c: TipoExamen.objects.filter(codigo=c, activo=True).exists()
        for c in ("ASP_ASC", "GLU_ASC", "ASP_LCR", "CITOL_ESP")
    },
)
print(
    "EXTRA_CULTIVOS_MISSING",
    [
        c
        for c, _, _ in CULTIVOS_MICRO_EXTRA
        if not TipoCultivoMicrobiologia.objects.filter(codigo=c, activo=True).exists()
    ],
)
print(
    "EXTRA_MUESTRAS_MISSING",
    [
        c
        for c, _, _ in MUESTRAS_MICRO_EXTRA
        if not TipoMuestraMicrobiologia.objects.filter(codigo=c, activo=True).exists()
    ],
)
print("DONE")
