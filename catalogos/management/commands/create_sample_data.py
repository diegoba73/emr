from django.core.management.base import BaseCommand
from catalogos.models import CentroFisico, TipoAtencion


class Command(BaseCommand):
    help = 'Crea datos de prueba para centros físicos y tipos de atención'

    def handle(self, *args, **options):
        self.stdout.write('Creando centros físicos de prueba...')
        
        # Crear centros físicos
        centros_data = [
            {
                'codigo': 'CEHTA',
                'nombre': 'CEHTA - Centro de Atención Ambulatoria',
                'descripcion': 'Centro especializado en atención ambulatoria y consultas externas',
                'direccion': 'Av. Principal 123, Ciudad',
                'telefono': '011-1234-5678'
            },
            {
                'codigo': 'ICPL',
                'nombre': 'ICPL - Instituto Cardiológico con Internación',
                'descripcion': 'Instituto especializado en cardiología con capacidad de internación',
                'direccion': 'Calle Secundaria 456, Ciudad',
                'telefono': '011-9876-5432'
            }
        ]
        
        for centro_data in centros_data:
            centro, created = CentroFisico.objects.get_or_create(
                codigo=centro_data['codigo'],
                defaults=centro_data
            )
            if created:
                self.stdout.write(f'✅ Creado centro: {centro.nombre}')
            else:
                self.stdout.write(f'⚠️ Centro ya existe: {centro.nombre}')
        
        # Crear tipos de atención
        tipos_data = [
            # CEHTA
            {
                'codigo': 'AMBULATORIA',
                'nombre': 'Atención Ambulatoria',
                'descripcion': 'Consultas ambulatorias y atención sin internación',
                'centro_fisico': 'CEHTA',
                'requiere_internacion': False,
                'es_urgencia': False
            },
            # ICPL
            {
                'codigo': 'GUARDIA_CARDIOLOGICA',
                'nombre': 'Guardia Cardiológica',
                'descripcion': 'Atención de urgencias cardiológicas',
                'centro_fisico': 'ICPL',
                'requiere_internacion': False,
                'es_urgencia': True
            },
            {
                'codigo': 'INTERNACION_UCO',
                'nombre': 'Internación UCO (Terapia Intensiva)',
                'descripcion': 'Internación en Unidad de Cuidados Intensivos',
                'centro_fisico': 'ICPL',
                'requiere_internacion': True,
                'es_urgencia': False
            },
            {
                'codigo': 'INTERNACION_UCE',
                'nombre': 'Internación UCE (Observación/Intermedia)',
                'descripcion': 'Internación en Unidad de Cuidados Especiales',
                'centro_fisico': 'ICPL',
                'requiere_internacion': True,
                'es_urgencia': False
            },
            {
                'codigo': 'CIRUGIA_AMBULATORIA',
                'nombre': 'Cirugía Ambulatoria',
                'descripcion': 'Procedimientos quirúrgicos sin internación',
                'centro_fisico': 'ICPL',
                'requiere_internacion': False,
                'es_urgencia': False
            },
            {
                'codigo': 'CIRUGIA_COMPLEJA',
                'nombre': 'Cirugía Compleja con Internación',
                'descripcion': 'Procedimientos quirúrgicos complejos que requieren internación',
                'centro_fisico': 'ICPL',
                'requiere_internacion': True,
                'es_urgencia': False
            }
        ]
        
        for tipo_data in tipos_data:
            centro_fisico = CentroFisico.objects.get(codigo=tipo_data['centro_fisico'])
            tipo, created = TipoAtencion.objects.get_or_create(
                codigo=tipo_data['codigo'],
                defaults={
                    'nombre': tipo_data['nombre'],
                    'descripcion': tipo_data['descripcion'],
                    'centro_fisico': centro_fisico,
                    'requiere_internacion': tipo_data['requiere_internacion'],
                    'es_urgencia': tipo_data['es_urgencia']
                }
            )
            if created:
                self.stdout.write(f'✅ Creado tipo: {tipo.nombre}')
            else:
                self.stdout.write(f'⚠️ Tipo ya existe: {tipo.nombre}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Datos de prueba creados exitosamente!\n'
                f'   Centros físicos: {CentroFisico.objects.count()}\n'
                f'   Tipos de atención: {TipoAtencion.objects.count()}'
            )
        )


