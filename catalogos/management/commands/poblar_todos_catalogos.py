"""
Ejecuta la carga de todos los catálogos clínicos desde fuentes oficiales.

Incluye: CIE-10, procedimientos, estudios, medicamentos (ATC), especialidades
y catálogos de microbiología (medios, microorganismos, antibióticos).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Pobla CIE-10, procedimientos, estudios, medicamentos, especialidades '
        'y catálogos de microbiología'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar cada tabla antes de cargar',
        )
        parser.add_argument(
            '--skip-cie10',
            action='store_true',
            help='Omitir CIE-10 (ya cargado)',
        )

    def handle(self, *args, **options):
        clear = ['--clear'] if options['clear'] else []
        steps = []
        if not options['skip_cie10']:
            steps.append(('poblar_cie10', 'CIE-10 diagnósticos'))
        steps.extend(
            [
                ('poblar_procedimientos', 'Procedimientos CIE-10-ES'),
                ('poblar_estudios', 'Estudios RadLex'),
                ('poblar_medicamentos', 'Medicamentos ATC/DDD'),
                ('poblar_especialidades', 'Especialidades médicas AR'),
                ('poblar_microbiologia_medios', 'Microbiología — Medios de cultivo'),
                ('poblar_microbiologia_microorganismos', 'Microbiología — Microorganismos'),
                ('poblar_microbiologia_antibioticos', 'Microbiología — Antibióticos'),
            ]
        )

        for cmd, label in steps:
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {label} ==='))
            call_command(cmd, *clear)

        self.stdout.write(self.style.SUCCESS('\n✅ Todos los catálogos cargados.'))
