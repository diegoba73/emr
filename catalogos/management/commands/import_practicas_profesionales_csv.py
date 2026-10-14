"""
Import aditivo de prácticas y profesionales desde CSV (producción segura).

  python manage.py import_practicas_profesionales_csv \\
      --practicas /ruta/practicas.csv \\
      --profesionales /ruta/profesionales.csv \\
      [--dry-run] [--solo-nuevos]

Por defecto --solo-nuevos: solo crea faltantes; no actualiza ni desactiva existentes.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogos.models import EstudioDiagnostico
from estudios.models import TipoEstudioComplementario
from estudios.practicas_cehta import slug_practica
from medicos.models import Especialidad
from profesionales.models import Profesional


def _norm_key(s: str) -> str:
    nfkd = unicodedata.normalize('NFKD', (s or '').strip().upper())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _parse_apellido_nombre(profesional: str) -> tuple[str, str]:
    parts = [p for p in (profesional or '').strip().split() if p]
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0].title(), ''
    return parts[0].title(), ' '.join(parts[1:]).title()


def _matricula_sintetica(prefix: str, apellido: str, nombre: str) -> str:
    base = _norm_key(f'{apellido}_{nombre}')
    base = re.sub(r'[^A-Z0-9]+', '_', base).strip('_')[:40] or 'X'
    return f'{prefix}-{base}'[:50]


def _read_practicas(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-8-sig')
    # Una columna; puede venir con header PRACTICAS o sin header.
    names: list[str] = []
    seen: set[str] = set()
    reader = csv.reader(text.splitlines())
    for row in reader:
        if not row:
            continue
        nombre = (row[0] or '').strip().strip('"')
        if not nombre or _norm_key(nombre) in {'PRACTICAS', 'PRACTICA', 'NOMBRE'}:
            continue
        key = _norm_key(nombre)
        if key in seen:
            continue
        seen.add(key)
        names.append(nombre)
    return names


def _read_profesionales(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding='utf-8-sig')
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise CommandError(f'Sin encabezados en {path}')
    # Normalizar nombres de columna
    fields = {_norm_key(f): f for f in reader.fieldnames if f}
    col_prof = fields.get('PROFESIONAL') or fields.get('NOMBRE')
    col_esp = fields.get('ESPECIALIDAD')
    if not col_prof:
        raise CommandError(f'No encuentro columna PROFESIONAL en {path}: {reader.fieldnames}')
    for raw in reader:
        profesional = (raw.get(col_prof) or '').strip()
        especialidad = (raw.get(col_esp) or '').strip() if col_esp else ''
        if not profesional:
            continue
        key = _norm_key(profesional)
        if key in seen:
            continue
        seen.add(key)
        rows.append((profesional, especialidad))
    return rows


class Command(BaseCommand):
    help = 'Importa prácticas y profesionales desde CSV (aditivo / --solo-nuevos).'

    def add_arguments(self, parser):
        parser.add_argument('--practicas', type=str, default='', help='Ruta a practicas.csv')
        parser.add_argument('--profesionales', type=str, default='', help='Ruta a profesionales.csv')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--solo-nuevos',
            action='store_true',
            default=True,
            help='Solo crea faltantes (default: True).',
        )
        parser.add_argument(
            '--allow-update',
            action='store_true',
            help='Permite reactivar/actualizar existentes (desactiva el modo solo-nuevos).',
        )

    def handle(self, *args, **options):
        dry = bool(options['dry_run'])
        solo_nuevos = not bool(options['allow_update'])
        practicas_path = Path(options['practicas']).expanduser() if options['practicas'] else None
        prof_path = Path(options['profesionales']).expanduser() if options['profesionales'] else None

        if not practicas_path and not prof_path:
            raise CommandError('Indicá --practicas y/o --profesionales')

        practicas: list[str] = []
        profesionales: list[tuple[str, str]] = []
        if practicas_path:
            if not practicas_path.is_file():
                raise CommandError(f'No existe {practicas_path}')
            practicas = _read_practicas(practicas_path)
        if prof_path:
            if not prof_path.is_file():
                raise CommandError(f'No existe {prof_path}')
            profesionales = _read_profesionales(prof_path)

        self.stdout.write(
            f'Prácticas CSV={len(practicas)} Profesionales CSV={len(profesionales)}'
            + (' [DRY-RUN]' if dry else '')
            + (' [SOLO-NUEVOS]' if solo_nuevos else ' [ALLOW-UPDATE]')
        )

        stats = {
            'tipo_created': 0,
            'tipo_skipped': 0,
            'tipo_updated': 0,
            'estudio_created': 0,
            'estudio_skipped': 0,
            'estudio_updated': 0,
            'esp_created': 0,
            'prof_created': 0,
            'prof_skipped': 0,
            'prof_updated': 0,
        }

        with transaction.atomic():
            if practicas:
                self._import_practicas(practicas, stats, dry=dry, solo_nuevos=solo_nuevos)
            if profesionales:
                self._import_profesionales(profesionales, stats, dry=dry, solo_nuevos=solo_nuevos)
            if dry:
                transaction.set_rollback(True)

        for k, v in stats.items():
            self.stdout.write(f'  {k}: {v}')
        self.stdout.write(self.style.SUCCESS('Import CSV finalizado.'))

    def _import_practicas(self, practicas, stats, *, dry: bool, solo_nuevos: bool):
        for nombre in practicas:
            codigo = slug_practica(nombre)[:50]
            tipo = TipoEstudioComplementario.objects.filter(codigo=codigo).first()
            if tipo is None:
                # también match por nombre por si el código difiere
                tipo = TipoEstudioComplementario.objects.filter(nombre__iexact=nombre).first()

            if tipo is None:
                stats['tipo_created'] += 1
                self.stdout.write(f'  TipoEstudio crear: {nombre} ({codigo})')
                if not dry:
                    TipoEstudioComplementario.objects.create(
                        codigo=codigo,
                        nombre=nombre[:255],
                        practica=codigo,
                        requiere_informe=True,
                        activo=True,
                        descripcion='Práctica CEHTA',
                    )
            elif solo_nuevos:
                stats['tipo_skipped'] += 1
            else:
                fields: list[str] = []
                if not tipo.activo:
                    tipo.activo = True
                    fields.append('activo')
                if tipo.nombre != nombre[:255]:
                    tipo.nombre = nombre[:255]
                    fields.append('nombre')
                if fields and not dry:
                    tipo.save(update_fields=fields)
                    stats['tipo_updated'] += 1
                    self.stdout.write(f'  TipoEstudio actualizar: {nombre}')
                else:
                    stats['tipo_skipped'] += 1

            estudio = EstudioDiagnostico.objects.filter(nombre__iexact=nombre).first()
            if estudio is None:
                stats['estudio_created'] += 1
                self.stdout.write(f'  EstudioDiagnostico crear: {nombre}')
                if not dry:
                    EstudioDiagnostico.objects.create(
                        nombre=nombre,
                        descripcion='Práctica CEHTA',
                        activo=True,
                    )
            elif solo_nuevos:
                stats['estudio_skipped'] += 1
            else:
                fields = []
                if not estudio.activo:
                    estudio.activo = True
                    fields.append('activo')
                if fields and not dry:
                    estudio.save(update_fields=fields)
                    stats['estudio_updated'] += 1
                else:
                    stats['estudio_skipped'] += 1

    def _import_profesionales(self, rows, stats, *, dry: bool, solo_nuevos: bool):
        for profesional, especialidad in rows:
            apellido, nombre = _parse_apellido_nombre(profesional)
            if not apellido:
                continue
            esp = self._get_or_create_esp(especialidad, stats, dry=dry)
            prof = (
                Profesional.objects.filter(apellido__iexact=apellido, nombre__iexact=nombre)
                .order_by('id')
                .first()
            )
            if prof is None:
                stats['prof_created'] += 1
                matricula = _matricula_sintetica('PROF', apellido, nombre)
                self.stdout.write(
                    f'  Profesional crear: {apellido}, {nombre} / {especialidad} ({matricula})'
                )
                if not dry:
                    if Profesional.objects.filter(matricula=matricula).exists():
                        matricula = f'{matricula}-{Profesional.objects.count() + 1}'[:50]
                    Profesional.objects.create(
                        apellido=apellido,
                        nombre=nombre,
                        matricula=matricula,
                        especialidad=esp,
                    )
            elif solo_nuevos:
                stats['prof_skipped'] += 1
                self.stdout.write(f'  Profesional omitir (ya existe): {apellido}, {nombre}')
            else:
                if esp and prof.especialidad_id != esp.id and not dry:
                    prof.especialidad = esp
                    prof.save(update_fields=['especialidad', 'ultima_actualizacion'])
                    stats['prof_updated'] += 1
                    self.stdout.write(f'  Profesional actualizar esp: {apellido}, {nombre}')
                else:
                    stats['prof_skipped'] += 1

    def _get_or_create_esp(self, nombre: str, stats: dict, *, dry: bool) -> Especialidad | None:
        nombre = (nombre or '').strip()
        if not nombre:
            return None
        existing = Especialidad.objects.filter(nombre__iexact=nombre).first()
        if existing:
            return existing
        # match sin acento
        for esp in Especialidad.objects.all().only('id', 'nombre'):
            if _norm_key(esp.nombre) == _norm_key(nombre):
                return esp
        display = nombre.title() if nombre == nombre.upper() else nombre
        stats['esp_created'] += 1
        self.stdout.write(f'  Especialidad crear: {display}')
        if dry:
            return None
        return Especialidad.objects.create(
            nombre=display,
            descripcion=f'Especialidad importada CEHTA — {display}',
        )
