"""Seed idempotente del catálogo quirúrgico jerárquico desde catalogos/data/cirugias.csv."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from catalogos.models import CirugiaAbordaje, CirugiaEspecialidad, CirugiaProcedimiento

DEFAULT_CSV = Path(__file__).resolve().parents[2] / 'data' / 'cirugias.csv'

# Partir "A, B o C" / "A o B" en abordajes; no partir "A y B".
_SPLIT_ABORDAJE = re.compile(r'\s*,\s*|\s+o\s+', re.IGNORECASE)


def split_abordajes(tipo: str) -> list[str]:
    raw = (tipo or '').strip().strip('"').strip()
    if not raw:
        return []
    parts = [p.strip() for p in _SPLIT_ABORDAJE.split(raw) if p.strip()]
    # Capitalizar solo si quedó en minúscula por el split (p. ej. "abierto").
    out = []
    for p in parts:
        if p and p[0].islower():
            p = p[0].upper() + p[1:]
        out.append(p)
    return out or [raw]


def parse_cirugias_csv(path: Path) -> list[tuple[str, str, list[str]]]:
    """Devuelve lista (especialidad, procedimiento, abordajes)."""
    rows: list[tuple[str, str, list[str]]] = []
    especialidad: str | None = None
    with path.open(encoding='utf-8-sig', newline='') as fh:
        reader = csv.reader(fh)
        for row in reader:
            cells = [(c or '').strip() for c in row]
            while cells and cells[-1] == '':
                cells.pop()
            if not cells or all(c == '' for c in cells):
                continue
            # Sección: ",Ginecología," → ['', 'Ginecología'] o ['Ginecología']
            non_empty = [c for c in cells if c]
            if len(non_empty) == 1 and non_empty[0].lower() not in ('procedimiento', 'tipo'):
                # Header de especialidad (única celda no vacía, no es cabecera de tabla).
                if cells[0] == '' or (len(cells) >= 2 and cells[0] == ''):
                    especialidad = non_empty[0]
                    continue
                if len(cells) == 1:
                    especialidad = non_empty[0]
                    continue
            if len(cells) >= 2 and cells[0].lower() == 'procedimiento':
                continue
            if especialidad is None:
                continue
            if len(cells) < 1 or not cells[0]:
                continue
            proc_nombre = cells[0]
            tipo = cells[1] if len(cells) > 1 else ''
            rows.append((especialidad, proc_nombre, split_abordajes(tipo)))
    return rows


class Command(BaseCommand):
    help = 'Pobla CirugiaEspecialidad / CirugiaProcedimiento / CirugiaAbordaje desde CSV.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default=str(DEFAULT_CSV),
            help='Ruta al CSV (default: catalogos/data/cirugias.csv)',
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        path = Path(options['csv'])
        dry = options['dry_run']
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'No existe CSV: {path}'))
            return

        parsed = parse_cirugias_csv(path)
        stats = {'esp_new': 0, 'esp_ex': 0, 'proc_new': 0, 'proc_ex': 0, 'abr_new': 0, 'abr_ex': 0}
        orden = 0
        seen_esp: dict[str, CirugiaEspecialidad | None] = {}

        for esp_nombre, proc_nombre, abordajes in parsed:
            if esp_nombre not in seen_esp:
                orden += 10
                if dry:
                    exists = CirugiaEspecialidad.objects.filter(nombre__iexact=esp_nombre).exists()
                    stats['esp_ex' if exists else 'esp_new'] += 1
                    seen_esp[esp_nombre] = None
                    esp = None
                else:
                    esp, created = CirugiaEspecialidad.objects.get_or_create(
                        nombre=esp_nombre,
                        defaults={'activo': True, 'orden': orden},
                    )
                    stats['esp_new' if created else 'esp_ex'] += 1
                    if not created and esp.orden == 0:
                        esp.orden = orden
                        esp.save(update_fields=['orden'])
                    seen_esp[esp_nombre] = esp
            else:
                esp = seen_esp[esp_nombre]

            if dry:
                exists_p = CirugiaProcedimiento.objects.filter(
                    especialidad__nombre__iexact=esp_nombre,
                    nombre__iexact=proc_nombre,
                ).exists()
                stats['proc_ex' if exists_p else 'proc_new'] += 1
                for abr in abordajes:
                    exists_a = CirugiaAbordaje.objects.filter(
                        procedimiento__especialidad__nombre__iexact=esp_nombre,
                        procedimiento__nombre__iexact=proc_nombre,
                        nombre__iexact=abr,
                    ).exists()
                    stats['abr_ex' if exists_a else 'abr_new'] += 1
                continue

            assert esp is not None
            proc, created_p = CirugiaProcedimiento.objects.get_or_create(
                especialidad=esp,
                nombre=proc_nombre,
                defaults={'activo': True},
            )
            stats['proc_new' if created_p else 'proc_ex'] += 1
            for abr in abordajes:
                _, created_a = CirugiaAbordaje.objects.get_or_create(
                    procedimiento=proc,
                    nombre=abr,
                    defaults={'activo': True},
                )
                stats['abr_new' if created_a else 'abr_ex'] += 1

        prefix = '[dry-run] ' if dry else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefix}especialidades +{stats["esp_new"]}/={stats["esp_ex"]} '
                f'procedimientos +{stats["proc_new"]}/={stats["proc_ex"]} '
                f'abordajes +{stats["abr_new"]}/={stats["abr_ex"]} '
                f'(filas CSV={len(parsed)})'
            )
        )
