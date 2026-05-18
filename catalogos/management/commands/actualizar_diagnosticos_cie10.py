import csv
import os
import requests
import io
from django.core.management.base import BaseCommand
from django.conf import settings
from catalogos.models import DiagnosticoCIE10
from django.db import transaction


class Command(BaseCommand):
    help = 'Actualiza diagnósticos CIE-10 desde una fuente actualizada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            help='Ruta al archivo CSV con los diagnósticos (opcional)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar todos los diagnósticos existentes antes de cargar'
        )
        parser.add_argument(
            '--url',
            type=str,
            help='URL del archivo CSV a descargar (opcional)'
        )

    def handle(self, *args, **options):
        csv_file = options.get('csv_file')
        clear_existing = options.get('clear', False)
        url = options.get('url')

        # Limpiar datos existentes si se solicita
        if clear_existing:
            count_deleted = DiagnosticoCIE10.objects.count()
            DiagnosticoCIE10.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Se eliminaron {count_deleted} diagnósticos existentes')
            )

        # Determinar fuente de datos
        csv_content = None
        
        if url:
            # Descargar desde URL
            self.stdout.write(f'Descargando diagnósticos desde: {url}')
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                csv_content = io.StringIO(response.text)
                self.stdout.write(self.style.SUCCESS('Archivo descargado exitosamente'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error descargando archivo: {str(e)}')
                )
                return
        elif csv_file:
            # Usar archivo local
            if not os.path.exists(csv_file):
                self.stdout.write(
                    self.style.ERROR(f'El archivo {csv_file} no existe')
                )
                return
            csv_content = open(csv_file, 'r', encoding='utf-8')
        else:
            # Intentar usar archivo por defecto o mostrar instrucciones
            default_path = os.path.join(settings.BASE_DIR, 'data', 'cie10_completo.csv')
            if os.path.exists(default_path):
                csv_content = open(default_path, 'r', encoding='utf-8')
                self.stdout.write(f'Usando archivo por defecto: {default_path}')
            else:
                self.stdout.write(
                    self.style.ERROR(
                        'No se proporcionó archivo CSV ni URL.\n'
                        'Opciones:\n'
                        '1. Usar --csv-file /ruta/al/archivo.csv\n'
                        '2. Usar --url https://url-del-archivo.csv\n'
                        '3. Colocar un archivo cie10_completo.csv en la carpeta data/\n\n'
                        'Puedes descargar la lista completa de CIE-10 desde:\n'
                        '- Ministerio de Sanidad (España): https://www.sanidad.gob.es/estadEstudios/estadisticas/normalizacion/CIE10/\n'
                        '- WHO ICD-10: https://www.who.int/standards/classifications/classification-of-diseases'
                    )
                )
                return

        # Contador para estadísticas
        created_count = 0
        updated_count = 0
        error_count = 0
        skipped_count = 0

        try:
            # Detectar delimitador y encoding
            sample = csv_content.read(1024)
            csv_content.seek(0)
            
            # Intentar diferentes delimitadores
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csv_content, delimiter=delimiter)
            
            # Detectar nombres de columnas (flexible)
            fieldnames = reader.fieldnames
            if not fieldnames:
                self.stdout.write(self.style.ERROR('No se pudieron detectar columnas en el CSV'))
                return
            
            self.stdout.write(f'Columnas detectadas: {", ".join(fieldnames)}')
            
            # Mapeo flexible de columnas
            def get_field(row, possible_names):
                for name in possible_names:
                    if name in row and row[name]:
                        return row[name].strip()
                return ''
            
            batch_size = 1000
            batch = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Mapear campos con diferentes nombres posibles
                        codigo = get_field(row, ['codigo', 'code', 'Código', 'Code', 'CODIGO', 'CODE'])
                        descripcion = get_field(row, ['descripcion', 'description', 'Descripción', 'Description', 'DESCRIPCION', 'DESCRIPTION', 'desc', 'Desc'])
                        capitulo = get_field(row, ['capitulo', 'chapter', 'Capítulo', 'Chapter', 'CAPITULO', 'CHAPTER'])
                        enfermedad = get_field(row, ['enfermedad', 'disease', 'Enfermedad', 'Disease', 'ENFERMEDAD', 'DISEASE'])
                        tipo_enfermedad = get_field(row, ['tipo_enfermedad', 'tipo de enfermedad', 'disease_type', 'Tipo de Enfermedad', 'Disease Type'])
                        categoria = get_field(row, ['categoria', 'category', 'Categoría', 'Category', 'CATEGORIA', 'CATEGORY'])
                        
                        # Validar que al menos código y descripción estén presentes
                        if not codigo:
                            skipped_count += 1
                            continue
                        
                        if not descripcion:
                            # Si no hay descripción, usar el código como descripción temporal
                            descripcion = codigo
                        
                        # Crear o actualizar diagnóstico
                        diagnostico, created = DiagnosticoCIE10.objects.get_or_create(
                            codigo=codigo,
                            defaults={
                                'descripcion': descripcion[:5000] if len(descripcion) > 5000 else descripcion,
                                'capitulo': capitulo[:100] if capitulo else None,
                                'enfermedad': enfermedad[:200] if enfermedad else None,
                                'tipo_enfermedad': tipo_enfermedad[:200] if tipo_enfermedad else None,
                                'categoria': categoria[:100] if categoria else codigo[:3] if len(codigo) >= 3 else codigo,
                                'activo': True
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            # Actualizar campos existentes
                            diagnostico.descripcion = descripcion[:5000] if len(descripcion) > 5000 else descripcion
                            if capitulo:
                                diagnostico.capitulo = capitulo[:100]
                            if enfermedad:
                                diagnostico.enfermedad = enfermedad[:200]
                            if tipo_enfermedad:
                                diagnostico.tipo_enfermedad = tipo_enfermedad[:200]
                            if categoria:
                                diagnostico.categoria = categoria[:100]
                            diagnostico.activo = True
                            diagnostico.save()
                            updated_count += 1
                        
                        # Procesar en lotes para mejor rendimiento
                        if (created_count + updated_count) % batch_size == 0:
                            self.stdout.write(f'Procesados {created_count + updated_count} diagnósticos...')
                    
                    except Exception as e:
                        error_count += 1
                        if error_count <= 10:  # Mostrar solo los primeros 10 errores
                            self.stdout.write(
                                self.style.ERROR(f'Error en fila {row_num}: {str(e)}')
                            )
                        elif error_count == 11:
                            self.stdout.write(
                                self.style.WARNING('... (más errores, pero no se mostrarán)')
                            )

            # Mostrar estadísticas finales
            total_count = DiagnosticoCIE10.objects.count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n{"="*60}\n'
                    f'Carga completada exitosamente:\n'
                    f'- Diagnósticos creados: {created_count}\n'
                    f'- Diagnósticos actualizados: {updated_count}\n'
                    f'- Filas omitidas: {skipped_count}\n'
                    f'- Errores: {error_count}\n'
                    f'- Total en base de datos: {total_count}\n'
                    f'{"="*60}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error general: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
        finally:
            if csv_content and hasattr(csv_content, 'close'):
                csv_content.close()



