"""
Carga Antibiotico desde índice ATC/DDD de la OMS (grupo J01 — antibacterianos sistémicos).

Fuente: WHO Collaborating Centre for Drug Statistics Methodology (mismo CSV que
``poblar_medicamentos``). Reutiliza ``data/atc_ddd_who.csv`` en caché.
"""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.management.catalog_sources import resolve_file
from catalogos.management.commands.poblar_medicamentos import DEFAULT_ATC_URL
from laboratorio.models_microbiologia import Antibiotico

J01_FAMILIAS = {
    'J01A': 'Tetraciclinas',
    'J01B': 'Anfenicoles',
    'J01C': 'Penicilinas beta-lactamasa',
    'J01D': 'Penicilinas',
    'J01E': 'Sulfonamidas y trimetoprim',
    'J01F': 'Macrólidos y lincosamidas',
    'J01G': 'Aminoglucósidos',
    'J01M': 'Quinolonas',
    'J01R': 'Combinaciones antibacterianas',
    'J01X': 'Otros antibacterianos',
}

BATCH_SIZE = 500


class Command(BaseCommand):
    help = 'Carga antibióticos desde ATC/DDD OMS (grupo J01)'

    def add_arguments(self, parser):
        parser.add_argument('--url', default=DEFAULT_ATC_URL, help='URL del CSV ATC/DDD')
        parser.add_argument('--file', dest='csv_file', help='CSV local ATC/DDD')
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        path = resolve_file(
            local_path=options.get('csv_file'),
            url=options['url'],
            cache_name='atc_ddd_who.csv',
        )
        records = self._parse_j01(path)
        self.stdout.write(f'Antibióticos J01 (nivel 5) parseados: {len(records)}')

        if options['dry_run']:
            for row in records[:5]:
                self.stdout.write(f"  {row['codigo']} — {row['nombre'][:60]}")
            return

        if options['clear']:
            deleted = Antibiotico.objects.count()
            Antibiotico.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminados {deleted} antibióticos'))

        created = self._bulk_insert(records)
        total = Antibiotico.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Carga completada: {created} insertados, {total} total')
        )

    def _parse_j01(self, path: str) -> list[dict]:
        content = Path(path).read_text(encoding='utf-8-sig')
        reader = csv.DictReader(StringIO(content))
        by_code: dict[str, dict] = {}

        for row in reader:
            code = (row.get('atc_code') or '').strip()
            name = (row.get('atc_name') or '').strip()
            if not code.startswith('J01') or len(code) != 7 or not name or name == 'NA':
                continue
            if code in by_code:
                continue

            ddd = (row.get('ddd') or '').strip()
            uom = (row.get('uom') or '').strip()
            adm = (row.get('adm_r') or '').strip()
            familia_key = code[:4]
            familia = J01_FAMILIAS.get(familia_key, familia_key)

            desc_parts = []
            if ddd and ddd != 'NA' and uom and uom != 'NA':
                desc_parts.append(f'DDD: {ddd} {uom}')
            if adm and adm != 'NA':
                desc_parts.append(f'Vía ATC: {adm}')

            by_code[code] = {
                'codigo': code[:40],
                'nombre': name.title()[:200],
                'familia': familia[:120],
                'descripcion': '; '.join(desc_parts),
                'activo': True,
            }
        return list(by_code.values())

    def _bulk_insert(self, records: list[dict]) -> int:
        existing = set(Antibiotico.objects.values_list('codigo', flat=True))
        to_create = [Antibiotico(**row) for row in records if row['codigo'] not in existing]
        created = 0
        with transaction.atomic():
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i : i + BATCH_SIZE]
                Antibiotico.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)
        return created
