from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from internacion.models import Sector, Cama, Internacion
from pacientes.models import Paciente
from medicos.models import Medico


class Command(BaseCommand):
    help = 'Crea sectores, camas y datos de prueba para el módulo de internación'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('INICIANDO SETUP DE INTERNACIÓN'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # 1. Crear Sectores
        self.stdout.write('\n📋 Creando sectores...')
        sector_uco, created = Sector.objects.get_or_create(nombre='UCO')
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Creado sector: {sector_uco.nombre}'))
        else:
            self.stdout.write(f'⚠️  Sector ya existe: {sector_uco.nombre}')
        
        sector_uce, created = Sector.objects.get_or_create(nombre='UCE')
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Creado sector: {sector_uce.nombre}'))
        else:
            self.stdout.write(f'⚠️  Sector ya existe: {sector_uce.nombre}')
        
        # 2. Crear Camas para UCO (6 camas, la 6 es aislada)
        self.stdout.write('\n🛏️  Creando camas para UCO...')
        camas_uco = []
        for i in range(1, 7):
            es_aislada = (i == 6)
            cama, created = Cama.objects.get_or_create(
                nombre=f'Cama {i}',
                sector=sector_uco,
                defaults={
                    'estado': 'DISPONIBLE',
                    'aislada': es_aislada
                }
            )
            # Actualizar si ya existe
            if not created and cama.aislada != es_aislada:
                cama.aislada = es_aislada
                cama.save()
            camas_uco.append(cama)
            if created:
                tipo = ' (Aislada)' if es_aislada else ''
                self.stdout.write(self.style.SUCCESS(f'✅ Creada: {cama.nombre}{tipo}'))
        
        # 3. Crear Camas para UCE (9 camas, la 9 es aislada)
        self.stdout.write('\n🛏️  Creando camas para UCE...')
        camas_uce = []
        for i in range(1, 10):
            es_aislada = (i == 9)
            cama, created = Cama.objects.get_or_create(
                nombre=f'Cama {i}',
                sector=sector_uce,
                defaults={
                    'estado': 'DISPONIBLE',
                    'aislada': es_aislada
                }
            )
            # Actualizar si ya existe
            if not created and cama.aislada != es_aislada:
                cama.aislada = es_aislada
                cama.save()
            camas_uce.append(cama)
            if created:
                tipo = ' (Aislada)' if es_aislada else ''
                self.stdout.write(self.style.SUCCESS(f'✅ Creada: {cama.nombre}{tipo}'))
        
        # 4. Buscar o crear pacientes
        self.stdout.write('\n👥 Verificando pacientes...')
        pacientes = list(Paciente.objects.all())
        if len(pacientes) < 5:
            self.stdout.write(self.style.WARNING(f'Solo hay {len(pacientes)} pacientes. Creando más...'))
            # Crear algunos pacientes de ejemplo
            nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Pedro', 'Sofía']
            apellidos = ['García', 'Rodríguez', 'López', 'Martínez', 'González', 'Pérez', 'Sánchez', 'Ramírez']
            
            for i in range(5 - len(pacientes)):
                nombre = random.choice(nombres)
                apellido = random.choice(apellidos)
                dni = f"{random.randint(20000000, 50000000)}"
                paciente, created = Paciente.objects.get_or_create(
                    dni=dni,
                    defaults={
                        'nombre': nombre,
                        'apellido': apellido,
                    }
                )
                if created:
                    pacientes.append(paciente)
                    self.stdout.write(self.style.SUCCESS(f'✅ Creado paciente: {paciente.apellido}, {paciente.nombre}'))
        
        self.stdout.write(f'✅ Total pacientes disponibles: {len(pacientes)}')
        
        # 5. Buscar o crear médicos
        self.stdout.write('\n👨‍⚕️ Verificando médicos...')
        medicos = list(Medico.objects.all())
        if len(medicos) < 2:
            self.stdout.write(self.style.WARNING(f'Solo hay {len(medicos)} médicos. Se necesitan al menos 2.'))
            # Intentar crear médicos básicos si no hay suficientes
            # Nota: Esto requiere usuarios, así que solo mostraremos advertencia
            self.stdout.write(self.style.WARNING('⚠️  Asegúrate de tener al menos 2 médicos en el sistema.'))
        
        if len(medicos) == 0:
            self.stdout.write(self.style.ERROR('❌ No hay médicos en el sistema. No se pueden crear internaciones.'))
            return
        
        self.stdout.write(f'✅ Total médicos disponibles: {len(medicos)}')
        
        # 6. Crear internaciones activas de ejemplo
        self.stdout.write('\n🏥 Creando internaciones de ejemplo...')
        todas_las_camas = camas_uco + camas_uce
        camas_disponibles = [c for c in todas_las_camas if c.estado == 'DISPONIBLE']
        
        if len(camas_disponibles) < 4:
            self.stdout.write(self.style.WARNING(f'⚠️  Solo hay {len(camas_disponibles)} camas disponibles. Creando menos internaciones.'))
            num_internaciones = len(camas_disponibles)
        else:
            num_internaciones = 4
        
        diagnosticos = [
            'Infarto agudo de miocardio',
            'Insuficiencia cardíaca congestiva',
            'Arritmia cardíaca compleja',
            'Postoperatorio de cirugía cardíaca',
            'Angina inestable',
            'Miocardiopatía dilatada',
        ]
        
        # Fechas de ingreso variables
        fechas_ingreso = [
            timezone.now(),  # Hoy
            timezone.now() - timedelta(days=3),  # Hace 3 días
            timezone.now() - timedelta(days=7),  # Hace 1 semana
            timezone.now() - timedelta(days=1),  # Ayer
        ]
        
        internaciones_creadas = 0
        for i in range(min(num_internaciones, len(camas_disponibles))):
            cama = camas_disponibles[i]
            paciente = random.choice(pacientes)
            medico = random.choice(medicos)
            diagnostico = random.choice(diagnosticos)
            fecha_ingreso = fechas_ingreso[i] if i < len(fechas_ingreso) else timezone.now() - timedelta(days=random.randint(1, 7))
            
            # Crear internación (el save() del modelo actualizará el estado de la cama)
            internacion = Internacion.objects.create(
                paciente=paciente,
                cama=cama,
                medico=medico,
                diagnostico_ingreso=diagnostico,
                fecha_ingreso=fecha_ingreso,
                activo=True
            )
            
            internaciones_creadas += 1
            dias = internacion.dias_internacion
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Internación creada: {paciente.apellido}, {paciente.nombre} en {cama.nombre} ({cama.sector.nombre}) - {dias} días'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('SETUP COMPLETADO EXITOSAMENTE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'\n📊 Resumen:')
        self.stdout.write(f'  - Sectores: 2 (UCO, UCE)')
        self.stdout.write(f'  - Camas UCO: {len(camas_uco)} (1 aislada: Cama 6)')
        self.stdout.write(f'  - Camas UCE: {len(camas_uce)} (1 aislada: Cama 9)')
        self.stdout.write(f'  - Internaciones activas: {internaciones_creadas}')

