"""
Carga EstudioDiagnostico desde RadLex Playbook (core).

Fuente: RSNA RadLex Playbook — estudios de imagen diagnóstica.
"""
from __future__ import annotations

import re

import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.management.catalog_sources import data_dir
from catalogos.management.radlex_traduccion_es import traducir_estudio_radlex
from catalogos.models import EstudioDiagnostico

DEFAULT_RADLEX_URL = 'https://services.rsna.org/playbook/v1/playbook/core'
BATCH_SIZE = 500
PLAYBOOK_TERM_RE = re.compile(
    r'<PlaybookTerm\b([^>]*?)(?:/>|>)',
    re.DOTALL,
)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


class Command(BaseCommand):
    help = 'Descarga y carga estudios diagnósticos (RadLex Playbook core)'

    def add_arguments(self, parser):
        parser.add_argument('--url', default=DEFAULT_RADLEX_URL)
        parser.add_argument('--file', dest='xml_file', help='XML local de RadLex Playbook')
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--lang',
            choices=('es', 'en'),
            default='es',
            help='Idioma de los nombres (es=glosario clínico, en=RadLex original)',
        )

    def handle(self, *args, **options):
        if options.get('xml_file'):
            path = options['xml_file']
        else:
            cache = data_dir() / 'radlex_playbook_core.xml'
            if cache.exists() and options['url'] == DEFAULT_RADLEX_URL:
                path = str(cache)
            else:
                self.stdout.write(f'Descargando RadLex Playbook desde {options["url"]}')
                response = requests.get(options['url'], timeout=180)
                response.raise_for_status()
                cache.write_bytes(response.content)
                path = str(cache)
                self.stdout.write(self.style.SUCCESS(f'Guardado en {cache}'))

        records = self._parse_xml(path, lang=options['lang'])
        self.stdout.write(f'Registros parseados: {len(records)}')

        if options['dry_run']:
            for row in records[:5]:
                self.stdout.write(f"  {row['nombre'][:80]}")
            return

        if options['clear']:
            deleted = EstudioDiagnostico.objects.count()
            EstudioDiagnostico.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminados {deleted} estudios'))

        created = self._bulk_insert(records)
        total = EstudioDiagnostico.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Carga completada: {created} insertados, {total} total')
        )

    def _parse_xml(self, path: str, *, lang: str = 'es') -> list[dict]:
        content = open(path, encoding='utf-8', errors='replace').read()
        records: list[dict] = []
        seen: set[str] = set()

        for match in PLAYBOOK_TERM_RE.finditer(content):
            attrs = dict(ATTR_RE.findall(match.group(1)))
            status = (attrs.get('status') or '').upper()
            if status and status not in ('ACTIVE', ''):
                continue
            long_name = (attrs.get('longName') or attrs.get('shortName') or '').strip()
            if not long_name:
                continue
            if lang == 'es':
                long_name = traducir_estudio_radlex(long_name)
            desc_en = (attrs.get('automatedLongDescription') or attrs.get('longName') or long_name).strip()
            rpid = attrs.get('radlexPlaybookId', '')
            nombre = long_name[:255]
            if nombre in seen:
                nombre = f'{nombre[:240]} ({rpid})'[:255]
            seen.add(nombre)
            descripcion = f'{rpid} — {desc_en}' if rpid else desc_en
            records.append(
                {
                    'nombre': nombre,
                    'descripcion': descripcion[:5000],
                    'activo': True,
                }
            )
        return records

    def _bulk_insert(self, records: list[dict]) -> int:
        existing = set(EstudioDiagnostico.objects.values_list('nombre', flat=True))
        to_create = [
            EstudioDiagnostico(**row)
            for row in records
            if row['nombre'] not in existing
        ]
        created = 0
        with transaction.atomic():
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i : i + BATCH_SIZE]
                EstudioDiagnostico.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)
        return created
