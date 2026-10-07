#!/usr/bin/env bash
set -euo pipefail
cd /home/diego/proyectos/emr
docker compose exec -T backend python manage.py shell <<'PY'
from django.db.models import Count
from estudios.models import TipoEstudioComplementario, EstudioComplementario
from estudios.practicas_cehta import CEHTA_PRACTICA_NOMBRES, slug_practica

cehta_codes = {slug_practica(n)[:50] for n in CEHTA_PRACTICA_NOMBRES}
print('tipos_total', TipoEstudioComplementario.objects.count())
print('tipos_cehta', TipoEstudioComplementario.objects.filter(practica__in=cehta_codes).count())
print('tipos_legacy', TipoEstudioComplementario.objects.filter(
    practica__in=['IMAGEN_RX','IMAGEN_TC','IMAGEN_RM','IMAGEN_US','PDF_INFORME_EXTERNO','OTRO']
).count())
print('sample_cehta:')
for t in TipoEstudioComplementario.objects.filter(practica__in=cehta_codes).order_by('nombre')[:5]:
    print(f'  {t.codigo} | {t.practica} | {t.nombre}')
print('estudios_por_practica:')
for row in EstudioComplementario.objects.values('practica').annotate(c=Count('id')).order_by('-c')[:12]:
    print(' ', row)
PY
