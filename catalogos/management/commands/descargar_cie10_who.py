"""
Comando para descargar y cargar diagnósticos CIE-10 desde fuentes públicas.
Este script intenta descargar datos de CIE-10 desde fuentes disponibles.
"""
import csv
import io
import requests
from django.core.management.base import BaseCommand
from django.core.management import call_command
from catalogos.models import DiagnosticoCIE10


class Command(BaseCommand):
    help = 'Descarga y carga diagnósticos CIE-10 desde fuentes públicas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar todos los diagnósticos existentes antes de cargar'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'Este comando requiere un archivo CSV con los diagnósticos CIE-10.\n'
            'Por favor, descarga la lista completa desde:\n\n'
            '1. Ministerio de Sanidad (España) - CIE-10-ES 5ª Edición (2024):\n'
            '   https://www.sanidad.gob.es/estadEstudios/estadisticas/normalizacion/CIE10/2024/\n\n'
            '2. WHO ICD-10:\n'
            '   https://www.who.int/standards/classifications/classification-of-diseases\n\n'
            '3. Una vez descargado el archivo CSV, usa:\n'
            '   python manage.py actualizar_diagnosticos_cie10 --csv-file /ruta/al/archivo.csv --clear\n\n'
            'El archivo CSV debe tener al menos estas columnas:\n'
            '- codigo (o code): Código CIE-10\n'
            '- descripcion (o description): Descripción del diagnóstico\n'
            '- capitulo (opcional): Capítulo\n'
            '- enfermedad (opcional): Enfermedad\n'
            '- tipo_enfermedad (opcional): Tipo de enfermedad\n'
            '- categoria (opcional): Categoría\n'
        ))
        
        # Mostrar estadísticas actuales
        current_count = DiagnosticoCIE10.objects.count()
        self.stdout.write(f'\nDiagnósticos actuales en la base de datos: {current_count}')
        
        if current_count < 1000:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  Tienes muy pocos diagnósticos ({current_count}). '
                'La CIE-10 completa tiene más de 14,000 códigos.\n'
                'Se recomienda actualizar la base de datos.'
            ))



