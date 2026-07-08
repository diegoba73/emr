"""
Carga Especialidad desde listado oficial MS Argentina (Res. 4011/23).

Fuente: https://www.argentina.gob.ar/servicio/certificado-de-especialista-sin-examen
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.management.catalog_sources import resolve_file
from medicos.models import Especialidad

DEFAULT_XLSX_URL = (
    'https://www.argentina.gob.ar/sites/default/files/2021/07/link_medicina.xlsx'
)


class Command(BaseCommand):
    help = 'Descarga y carga especialidades médicas oficiales (Argentina)'

    def add_arguments(self, parser):
        parser.add_argument('--url', default=DEFAULT_XLSX_URL)
        parser.add_argument('--file', dest='xlsx_file')
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError as exc:
            raise SystemExit('Falta openpyxl. Instalá con: pip install openpyxl') from exc

        path = resolve_file(
            local_path=options.get('xlsx_file'),
            url=options['url'],
            cache_name='especialidades_medicina_ar.xlsx',
        )
        records = self._parse(openpyxl, path)
        self.stdout.write(f'Registros parseados: {len(records)}')

        if options['dry_run']:
            for name in records[:10]:
                self.stdout.write(f'  {name}')
            return

        if options['clear']:
            deleted = Especialidad.objects.count()
            Especialidad.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminadas {deleted} especialidades'))

        created = 0
        updated = 0
        with transaction.atomic():
            for nombre in records:
                _, was_created = Especialidad.objects.update_or_create(
                    nombre=nombre,
                    defaults={'descripcion': f'Especialidad médica reconocida — {nombre}'},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        total = Especialidad.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Carga completada: {created} creadas, {updated} actualizadas, {total} total'
            )
        )

    def _parse(self, openpyxl, path: str) -> list[str]:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        names: list[str] = []
        seen: set[str] = set()

        for row in ws.iter_rows(values_only=True):
            for cell in row:
                text = (cell or '').strip() if isinstance(cell, str) else ''
                if not text:
                    continue
                lower = text.lower()
                if 'especialidad' in lower and 'medicina' in lower:
                    continue
                if lower.startswith('resolución') or lower.startswith('resolucion'):
                    continue
                if text not in seen:
                    seen.add(text)
                    names.append(text[:100])
        wb.close()
        return sorted(names, key=str.casefold)
