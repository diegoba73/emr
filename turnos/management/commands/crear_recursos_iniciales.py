from django.core.management.base import BaseCommand
from turnos.models import Recurso


class Command(BaseCommand):
    help = 'Crea recursos físicos iniciales (consultorios, quirófanos, salas)'

    def handle(self, *args, **options):
        recursos_iniciales = [
            # CEHTA - Consultorios
            {'nombre': 'Consultorio 101', 'ubicacion': 'CEHTA', 'tipo_recurso': 'CONSULTORIO'},
            {'nombre': 'Consultorio 102', 'ubicacion': 'CEHTA', 'tipo_recurso': 'CONSULTORIO'},
            {'nombre': 'Consultorio 103', 'ubicacion': 'CEHTA', 'tipo_recurso': 'CONSULTORIO'},
            {'nombre': 'Consultorio 104', 'ubicacion': 'CEHTA', 'tipo_recurso': 'CONSULTORIO'},
            {'nombre': 'Consultorio 105', 'ubicacion': 'CEHTA', 'tipo_recurso': 'CONSULTORIO'},
            
            # CEHTA - Salas de Procedimiento/Estudio
            {'nombre': 'Sala Eco Doppler', 'ubicacion': 'CEHTA', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
            {'nombre': 'Sala Ecocardiografía', 'ubicacion': 'CEHTA', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
            {'nombre': 'Sala Holter', 'ubicacion': 'CEHTA', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
            {'nombre': 'Sala Ergometría', 'ubicacion': 'CEHTA', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
            
            # ICPL - Quirófanos
            {'nombre': 'Quirófano 1', 'ubicacion': 'ICPL', 'tipo_recurso': 'QUIROFANO'},
            {'nombre': 'Quirófano 2', 'ubicacion': 'ICPL', 'tipo_recurso': 'QUIROFANO'},
            {'nombre': 'Quirófano 3', 'ubicacion': 'ICPL', 'tipo_recurso': 'QUIROFANO'},
            
            # ICPL - Salas de Hemodinamia
            {'nombre': 'Sala Hemodinamia 1', 'ubicacion': 'ICPL', 'tipo_recurso': 'SALA_HEMODINAMIA'},
            {'nombre': 'Sala Hemodinamia 2', 'ubicacion': 'ICPL', 'tipo_recurso': 'SALA_HEMODINAMIA'},
            
            # ICPL - Salas de Procedimiento
            {'nombre': 'Sala TAC', 'ubicacion': 'ICPL', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
            {'nombre': 'Sala Resonancia', 'ubicacion': 'ICPL', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
            {'nombre': 'Sala Ecografía', 'ubicacion': 'ICPL', 'tipo_recurso': 'SALA_PROCEDIMIENTO'},
        ]
        
        creados = 0
        actualizados = 0
        
        for recurso_data in recursos_iniciales:
            recurso, created = Recurso.objects.update_or_create(
                nombre=recurso_data['nombre'],
                defaults={
                    'ubicacion': recurso_data['ubicacion'],
                    'tipo_recurso': recurso_data['tipo_recurso'],
                    'activo': True
                }
            )
            
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Creado: {recurso}'))
            else:
                actualizados += 1
                self.stdout.write(self.style.WARNING(f'♻️ Actualizado: {recurso}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Proceso completado:'))
        self.stdout.write(f'  ➕ Recursos creados: {creados}')
        self.stdout.write(f'  ♻️ Recursos actualizados: {actualizados}')
        self.stdout.write(f'  📊 Total de recursos activos: {Recurso.objects.filter(activo=True).count()}')


