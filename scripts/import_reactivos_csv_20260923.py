"""Ejecutar con manage.py shell; aplica y verifica la importación autorizada."""
import csv
import json
from pathlib import Path
from django.core import serializers
from django.core.management import call_command
from django.db import transaction
from laboratorio.models_inventario import InsumoLab, LoteInsumo, MovimientoStock, ConsumoInsumoExamen
from laboratorio.management.commands.import_catalogo_reactivos_csv import planificar

backup = Path('docs/import-reactivos-respaldo-20260923.json')
if backup.exists():
    raise RuntimeError('Ya existe un respaldo: no repetir esta aplicación; usar simulación.')
models = [InsumoLab, LoteInsumo, MovimientoStock, ConsumoInsumoExamen]
backup.write_text(serializers.serialize('json', [obj for model in models for obj in model.objects.order_by('pk')], indent=2), encoding='utf-8')
with transaction.atomic():
    before = {m.__name__: serializers.serialize('json', m.objects.order_by('pk')) for m in models[1:]}
    call_command('import_catalogo_reactivos_csv', 'docs/Catalogo_reactivos.csv', apply=True,
                 report='docs/import-reactivos-aplicado-20260923.json')
    for model in models[1:]:
        assert before[model.__name__] == serializers.serialize('json', model.objects.order_by('pk')), model.__name__
    rows = list(csv.DictReader(open('docs/Catalogo_reactivos.csv', encoding='utf-8-sig')))
    plan = planificar(rows, list(InsumoLab.objects.all()))
    assert len(plan) == 53 and all(p['accion'] == 'sin_cambios' for p in plan), 'No idempotente'
    report = json.loads(Path('docs/import-reactivos-aplicado-20260923.json').read_text())
    new_ids = [p['id'] for p in report['productos'] if p['accion'] == 'crear']
    assert not LoteInsumo.objects.filter(insumo_id__in=new_ids).exists(), 'Altas con lotes inesperados'
print('VERIFICADO: 53 productos; segunda ejecución sin cambios; lotes, movimientos y consumos intactos; altas sin stock.')
