import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from catalogos.models import DiagnosticoCIE10


class Command(BaseCommand):
    help = 'Carga diagnósticos CIE-10 desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Ruta al archivo CSV con los diagnósticos'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar todos los diagnósticos existentes antes de cargar'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        clear_existing = options['clear']

        # Verificar que el archivo existe
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f'El archivo {csv_file} no existe')
            )
            return

        # Limpiar datos existentes si se solicita
        if clear_existing:
            count_deleted = DiagnosticoCIE10.objects.count()
            DiagnosticoCIE10.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Se eliminaron {count_deleted} diagnósticos existentes')
            )

        # Contador para estadísticas
        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    try:
                        # Mapear campos del CSV a los campos del modelo
                        codigo = row['codigo'].strip()
                        capitulo = row['capitulo'].strip()
                        enfermedad = row['enfermedad'].strip()
                        tipo_enfermedad = row['tipo de enfermedad'].strip()
                        descripcion = row['descripcion'].strip()

                        # Verificar si ya existe un diagnóstico con ese código
                        diagnostico, created = DiagnosticoCIE10.objects.get_or_create(
                            codigo=codigo,
                            defaults={
                                'capitulo': capitulo,
                                'enfermedad': enfermedad,
                                'tipo_enfermedad': tipo_enfermedad,
                                'descripcion': descripcion,
                                'activo': True
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            # Actualizar campos existentes
                            diagnostico.capitulo = capitulo
                            diagnostico.enfermedad = enfermedad
                            diagnostico.tipo_enfermedad = tipo_enfermedad
                            diagnostico.descripcion = descripcion
                            diagnostico.activo = True
                            diagnostico.save()
                            updated_count += 1

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Error procesando fila: {row} - Error: {str(e)}')
                        )

            # Mostrar estadísticas finales
            total_count = DiagnosticoCIE10.objects.count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Carga completada exitosamente:\n'
                    f'- Diagnósticos creados: {created_count}\n'
                    f'- Diagnósticos actualizados: {updated_count}\n'
                    f'- Errores: {error_count}\n'
                    f'- Total en base de datos: {total_count}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error general: {str(e)}')
            )

