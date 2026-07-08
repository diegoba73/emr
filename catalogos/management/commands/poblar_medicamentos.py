"""
Carga Medicamento desde índice ATC/DDD de la OMS.

Fuente: WHO Collaborating Centre for Drug Statistics Methodology (snapshot público).
Por defecto descarga el CSV más reciente del repositorio fabkury/atcd.
"""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.management.catalog_sources import resolve_file
from catalogos.models import Medicamento

DEFAULT_ATC_URL = (
    'https://github.com/fabkury/atcd/releases/download/april2026/'
    'WHO.ATC-DDD.2026-04-25.csv'
)
BATCH_SIZE = 1000

ADM_R_LABELS = {
    'O': 'Oral',
    'P': 'Parenteral',
    'R': 'Rectal',
    'N': 'Nasal',
    'V': 'Vaginal',
    'SL': 'Sublingual',
    'TD': 'Transdérmica',
    'Inhal': 'Inhalatoria',
    'Implant': 'Implante',
    'Instill': 'Instilación',
    'L': 'Local',
}


class Command(BaseCommand):
    help = 'Descarga y carga medicamentos desde índice ATC/DDD (OMS)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            default=DEFAULT_ATC_URL,
            help='URL del CSV ATC/DDD',
        )
        parser.add_argument('--file', dest='csv_file', help='CSV local ATC/DDD')
        parser.add_argument(
            '--legacy',
            action='store_true',
            help='Usar listado embebido reducido (cardiología/ginecología/oncología)',
        )
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--all-levels',
            action='store_true',
            help='Incluir todos los niveles ATC (por defecto solo nivel 5 / sustancia)',
        )

    def handle(self, *args, **options):
        if options['legacy']:
            from catalogos.management.commands._medicamentos_legacy import LEGACY_MEDICAMENTOS

            if options['clear']:
                deleted = Medicamento.objects.count()
                Medicamento.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'Eliminados {deleted} medicamentos'))
            created = updated = 0
            with transaction.atomic():
                for med_data in LEGACY_MEDICAMENTOS:
                    nombre_completo = (
                        f"{med_data['nombre']} {med_data['concentracion']} {med_data['presentacion']}"
                    )
                    _, was_created = Medicamento.objects.update_or_create(
                        nombre=nombre_completo,
                        defaults={
                            'principio_activo': med_data['principio_activo'],
                            'presentacion': med_data['presentacion'],
                            'concentracion': med_data['concentracion'],
                            'via_administracion': med_data['via_administracion'],
                            'codigo_atc': med_data.get('codigo_atc', ''),
                            'activo': True,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
            total = Medicamento.objects.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Legacy: {created} creados, {updated} actualizados, {total} total'
                )
            )
            return

        path = resolve_file(
            local_path=options.get('csv_file'),
            url=options['url'],
            cache_name='atc_ddd_who.csv',
        )
        records = self._parse_atc(path, all_levels=options['all_levels'])
        self.stdout.write(f'Registros ATC parseados: {len(records)}')

        if options['dry_run']:
            for row in records[:5]:
                self.stdout.write(f"  {row['nombre'][:70]}")
            return

        if options['clear']:
            deleted = Medicamento.objects.count()
            Medicamento.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminados {deleted} medicamentos'))

        created = self._bulk_upsert(records)
        total = Medicamento.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Carga completada: {created} nuevos, {total} total')
        )

    def _parse_atc(self, path: str, *, all_levels: bool) -> list[dict]:
        content = Path(path).read_text(encoding='utf-8-sig')
        reader = csv.DictReader(StringIO(content))
        records: list[dict] = []
        seen_atc: set[str] = set()

        for row in reader:
            code = (row.get('atc_code') or '').strip()
            name = (row.get('atc_name') or '').strip()
            if not code or not name or name == 'NA':
                continue
            if not all_levels and len(code) != 7:
                continue
            if code in seen_atc:
                continue
            seen_atc.add(code)

            ddd = (row.get('ddd') or '').strip()
            uom = (row.get('uom') or '').strip()
            adm = (row.get('adm_r') or '').strip()
            concentracion = f'{ddd} {uom}'.strip() if ddd and ddd != 'NA' else '—'
            via = ADM_R_LABELS.get(adm, adm if adm and adm != 'NA' else 'No especificada')

            display_name = name[:160]
            if len(name) > 160:
                display_name = f'{name[:157]}…'
            nombre = f'{display_name} ({code})'[:200]

            records.append(
                {
                    'nombre': nombre,
                    'principio_activo': name[:200],
                    'presentacion': 'Genérico / ATC',
                    'concentracion': concentracion[:50],
                    'via_administracion': via[:50],
                    'codigo_atc': code[:20],
                    'activo': True,
                }
            )
        return records

    def _bulk_upsert(self, records: list[dict]) -> int:
        existing_atc = set(
            Medicamento.objects.exclude(codigo_atc__isnull=True)
            .exclude(codigo_atc='')
            .values_list('codigo_atc', flat=True)
        )
        to_create = [
            Medicamento(**row)
            for row in records
            if row['codigo_atc'] not in existing_atc
        ]
        created = 0
        with transaction.atomic():
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i : i + BATCH_SIZE]
                Medicamento.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)
                if (i + BATCH_SIZE) % 5000 == 0 or i + BATCH_SIZE >= len(to_create):
                    self.stdout.write(f'  Insertados {min(i + BATCH_SIZE, len(to_create))}…')
        return created
