"""
Carga MedioCultivo desde lista de referencia CLSI/EUCAST.

Fuente: medios estándar de microbiología clínica (EUCAST disk diffusion / media
preparation, CLSI M41). El CSV se incluye en ``data/medios_cultivo_referencia.csv``.
"""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.management.catalog_sources import resolve_file
from laboratorio.models_microbiologia import MedioCultivo

BATCH_SIZE = 500


def _bundled_csv() -> str:
    return str(Path(settings.BASE_DIR) / 'data' / 'medios_cultivo_referencia.csv')


class Command(BaseCommand):
    help = 'Carga medios de cultivo desde CSV de referencia CLSI/EUCAST'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            dest='csv_file',
            help='CSV local (codigo,nombre,tipo,descripcion)',
        )
        parser.add_argument(
            '--url',
            default='',
            help='URL alternativa del CSV (por defecto usa data/medios_cultivo_referencia.csv)',
        )
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        if options.get('csv_file'):
            path = options['csv_file']
        elif options.get('url'):
            path = resolve_file(
                local_path=None,
                url=options['url'],
                cache_name='medios_cultivo_referencia.csv',
            )
        else:
            path = _bundled_csv()
            if not Path(path).exists():
                raise SystemExit(f'No se encontró el CSV embebido: {path}')

        records = self._parse(path)
        self.stdout.write(f'Registros parseados: {len(records)}')

        if options['dry_run']:
            for row in records[:5]:
                self.stdout.write(f"  {row['codigo']} — {row['nombre'][:60]}")
            return

        if options['clear']:
            deleted = MedioCultivo.objects.count()
            MedioCultivo.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminados {deleted} medios'))

        created = self._bulk_insert(records)
        total = MedioCultivo.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Carga completada: {created} insertados, {total} total')
        )

    def _parse(self, path: str) -> list[dict]:
        content = Path(path).read_text(encoding='utf-8-sig')
        reader = csv.DictReader(StringIO(content))
        records: list[dict] = []
        seen: set[str] = set()

        for row in reader:
            codigo = (row.get('codigo') or '').strip().upper()
            nombre = (row.get('nombre') or '').strip()
            if not codigo or not nombre:
                continue
            if codigo in seen:
                continue
            seen.add(codigo)
            records.append(
                {
                    'codigo': codigo[:30],
                    'nombre': nombre[:200],
                    'tipo': (row.get('tipo') or '').strip()[:50],
                    'descripcion': (row.get('descripcion') or '').strip(),
                    'activo': True,
                }
            )
        return records

    def _bulk_insert(self, records: list[dict]) -> int:
        existing = set(MedioCultivo.objects.values_list('codigo', flat=True))
        to_create = [MedioCultivo(**row) for row in records if row['codigo'] not in existing]
        created = 0
        with transaction.atomic():
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i : i + BATCH_SIZE]
                MedioCultivo.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)
        return created
