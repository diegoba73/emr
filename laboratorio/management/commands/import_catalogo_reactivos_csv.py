"""Importa productos del CSV fotográfico; nunca crea stock, lotes ni recetas."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from laboratorio.models_inventario import InsumoLab

# Correspondencias revisadas con el catálogo anterior. Los SKU son estables.
ALIASES = {
    ('Wiener lab.', 'HDL Cholesterol fast'): ('R-1009804', 'Wiener HDL Cholesterol fast'),
    ('Wiener lab.', 'Proti U/LCR'): ('R-1008161', 'Wiener Proti U/LCR'),
    ('Wiener lab.', 'Mg-color AA'): ('R-1008145', 'Wiener Mg-color AA'),
    ('Wiener lab.', 'UIBC/TIBC AA líquida'): ('R-1008123', 'Wiener UIBC/TIBC AA líquida'),
    ('Finecare', 'cTnI/CK-MB/Myo Rapid Quantitative Test'): ('R-W216', 'Finecare panel cTnI/Myoglobin/CK-MB'),
    ('Finecare', 'D-Dimer Rapid Quantitative Test'): ('R-W227', 'Finecare One Step D-Dimer Rapid Quantitative Test'),
}
# El propio CSV indica que estas referencias requieren comprobarse.
REF_PENDIENTE = {'6', '11', '19', '29', '31'}
MARCAS = {'Wiener lab.': 'Wiener', 'Finecare': 'Finecare', 'bioMérieux': 'bioMérieux'}


def planificar(rows, existentes):
    groups = {}
    for row in rows:
        key = (row['Fabricante / marca'], row['Producto (etiqueta)'], row['REF comercial'])
        groups.setdefault(key, []).append(row)
    plan = []
    used = set()
    for (marca, producto, ref), sources in groups.items():
        nombre = f"{MARCAS.get(marca, marca)} {producto}".strip()
        trusted_ref = ref if not any(r['ID foto'] in REF_PENDIENTE for r in sources) else ''
        fallback = 'CSV-REACT-' + sources[0]['ID foto']
        hits = [x for x in existentes if trusted_ref and x.ref_comercial == trusted_ref]
        if not hits:
            alias = ALIASES.get((marca, producto))
            hits = [x for x in existentes if x.codigo == fallback or x.nombre == nombre or (
                alias and x.codigo == alias[0] and x.nombre == alias[1])]
        if len(hits) > 1:
            raise CommandError(f'Coincidencia ambigua: {producto}')
        obj = hits[0] if hits else None
        if obj and obj.pk in used:
            raise CommandError(f'Dos productos resuelven al mismo SKU: {obj.codigo}')
        if obj:
            used.add(obj.pk)
        codigo = obj.codigo if obj else ('R-' + trusted_ref if trusted_ref else fallback)
        if not obj and any(x.codigo == codigo for x in existentes):
            raise CommandError(f'SKU ocupado: {codigo}')
        changes = {'nombre': nombre}
        if trusted_ref:
            changes['ref_comercial'] = trusted_ref
        if obj:
            changes = {k: v for k, v in changes.items() if getattr(obj, k) != v}
        else:
            clase = sources[0]['Clase']
            tipo = 'MEDIO' if clase == 'Medio de cultivo' else (
                'OTRO' if clase in {'Control', 'Control hematología', 'Calibrador', 'Solución limpieza'} else 'REACTIVO')
            changes.update(codigo=codigo, tipo=tipo, unidad='kit', ref_comercial=trusted_ref)
        plan.append({'id': obj.pk if obj else None, 'codigo': codigo,
                     'accion': 'crear' if obj is None else ('actualizar' if changes else 'sin_cambios'),
                     'antes': {k: getattr(obj, k) for k in changes} if obj else {},
                     'cambios': changes, 'fuente': sources})
    return plan


class Command(BaseCommand):
    help = 'Importa el catálogo fotográfico sin stock. Por defecto simula; --apply aplica con informe previo.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path')
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--report', required=True)

    def handle(self, *args, **options):
        source = Path(options['csv_path'])
        with source.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        required = {'ID foto', 'Producto (etiqueta)', 'Fabricante / marca', 'REF comercial', 'Clase'}
        if not rows or not required.issubset(rows[0]):
            raise CommandError('CSV vacío o columnas requeridas ausentes')
        if any(not r['ID foto'] or not r['Producto (etiqueta)'] for r in rows):
            raise CommandError('Producto o ID foto vacío')
        report_path = Path(options['report'])
        if report_path.exists():
            raise CommandError('El informe ya existe; elegí otra ruta para conservar el respaldo')
        with transaction.atomic():
            existing = list(InsumoLab.objects.select_for_update().all())
            plan = planificar(rows, existing)
            report = {'archivo': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                      'estado': 'preparado' if options['apply'] else 'simulacion',
                      'filas': len(rows), 'resumen': dict(Counter(p['accion'] for p in plan)),
                      'alcance': 'Solo catálogo: nombre, REF y altas. Sin lotes, stock, consumos ni QC. '
                                 'Fabricante, conservación, presentación y revisión se conservan en fuente; '
                                 'no se confunde fabricante con proveedor ni presentación con unidad de stock.',
                      'productos': plan}
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            if options['apply']:
                by_id = {x.pk: x for x in existing}
                for p in plan:
                    obj = by_id[p['id']] if p['id'] else InsumoLab()
                    for k, v in p['cambios'].items():
                        setattr(obj, k, v)
                    obj.full_clean()
                    if p['accion'] == 'crear':
                        obj.save()
                        p['id'] = obj.pk
                    elif p['cambios']:
                        obj.save(update_fields=[*p['cambios'], 'updated_at'])
        if options['apply']:
            report['estado'] = 'aplicado'
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps({'estado': report['estado'], **report['resumen'], 'informe': str(report_path)}, ensure_ascii=False))
