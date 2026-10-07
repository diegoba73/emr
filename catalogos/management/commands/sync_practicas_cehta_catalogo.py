"""
Upsert de prácticas CEHTA en el catálogo clínico (EstudioDiagnostico).

Aditivo / retrocompatible: no borra RadLex ni otros estudios; solo crea o
reactiva entradas por nombre (match case-insensitive) de CEHTA_PRACTICA_NOMBRES.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from catalogos.models import EstudioDiagnostico
from estudios.practicas_cehta import CEHTA_PRACTICA_NOMBRES

DESC_PREFIX = 'Práctica CEHTA'


class Command(BaseCommand):
    help = 'Sincroniza prácticas CEHTA hacia catalogos.EstudioDiagnostico (catálogo clínico).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra conteos sin escribir.',
        )

    def handle(self, *args, **options):
        dry = bool(options['dry_run'])
        creados = 0
        actualizados = 0
        sin_cambio = 0

        for nombre in CEHTA_PRACTICA_NOMBRES:
            nombre = (nombre or '').strip()
            if not nombre:
                continue
            estudio = EstudioDiagnostico.objects.filter(nombre__iexact=nombre).first()
            if estudio is None:
                if not dry:
                    EstudioDiagnostico.objects.create(
                        nombre=nombre,
                        descripcion=DESC_PREFIX,
                        activo=True,
                    )
                creados += 1
                continue

            fields: list[str] = []
            if not estudio.activo:
                estudio.activo = True
                fields.append('activo')
            if not (estudio.descripcion or '').strip():
                estudio.descripcion = DESC_PREFIX
                fields.append('descripcion')
            if fields:
                if not dry:
                    estudio.save(update_fields=fields)
                actualizados += 1
            else:
                sin_cambio += 1

        prefix = '[dry-run] ' if dry else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefix}CEHTA → EstudioDiagnostico: creados={creados} '
                f'actualizados={actualizados} sin_cambio={sin_cambio} '
                f'total_cehta={len(CEHTA_PRACTICA_NOMBRES)}'
            )
        )
