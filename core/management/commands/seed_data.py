"""
Comando de gestión Django para poblar la base de datos con datos iniciales.
Idempotente: usa get_or_create para no duplicar datos si se corre dos veces.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from catalogos.models import CentroFisico, TipoAtencion
from medicos.models import Especialidad, Medico
from laboratorio.models import TipoMuestra, TipoExamen
from pacientes.models import Paciente

User = get_user_model()


class Command(BaseCommand):
    """Comando Django para poblar datos iniciales."""
    
    help = 'Pobla la base de datos con datos iniciales (idempotente)'
    
    def handle(self, *args, **options):
        """Ejecuta el comando."""
        self.stdout.write(self.style.SUCCESS('Iniciando seeding de datos...'))
        
        # ========================================================================
        # 1. INFRAESTRUCTURA
        # ========================================================================
        self.stdout.write('Creando Centros Físicos...')
        
        centro_cehta, created = CentroFisico.objects.get_or_create(
            codigo='CEHTA',
            defaults={
                'nombre': 'CEHTA - Centro de Atención Ambulatoria',
                'descripcion': 'Centro de atención ambulatoria',
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {centro_cehta}'))
        else:
            self.stdout.write(f'  → Ya existe: {centro_cehta}')
        
        centro_pueblo, created = CentroFisico.objects.get_or_create(
            codigo='PUEBLO_DE_LUIS',
            defaults={
                'nombre': 'PUEBLO DE LUIS - Instituto Cardiológico con Internación',
                'descripcion': 'Instituto cardiológico con internación',
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {centro_pueblo}'))
        else:
            self.stdout.write(f'  → Ya existe: {centro_pueblo}')
        
        # Tipos de Atención
        self.stdout.write('Creando Tipos de Atención...')
        
        tipo_ambulatoria, created = TipoAtencion.objects.get_or_create(
            codigo='AMBULATORIA',
            defaults={
                'nombre': 'Consulta Ambulatoria',
                'centro_fisico': centro_cehta,
                'requiere_internacion': False,
                'es_urgencia': False,
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {tipo_ambulatoria}'))
        else:
            self.stdout.write(f'  → Ya existe: {tipo_ambulatoria}')
        
        tipo_guardia, created = TipoAtencion.objects.get_or_create(
            codigo='GUARDIA_CARDIOLOGICA',
            defaults={
                'nombre': 'Guardia Cardiológica',
                'centro_fisico': centro_pueblo,
                'requiere_internacion': False,
                'es_urgencia': True,
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {tipo_guardia}'))
        else:
            self.stdout.write(f'  → Ya existe: {tipo_guardia}')
        
        # Nota: No hay "Laboratorio" como TipoAtencion en el modelo actual
        # Si se necesita, se puede agregar después
        
        # Especialidades
        self.stdout.write('Creando Especialidades...')
        
        especialidades_data = [
            {'nombre': 'Cardiología', 'descripcion': 'Especialidad en enfermedades del corazón'},
            {'nombre': 'Clínica Médica', 'descripcion': 'Medicina general'},
            {'nombre': 'Traumatología', 'descripcion': 'Especialidad en traumatismos y ortopedia'},
        ]
        
        for esp_data in especialidades_data:
            especialidad, created = Especialidad.objects.get_or_create(
                nombre=esp_data['nombre'],
                defaults={'descripcion': esp_data['descripcion']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {especialidad}'))
            else:
                self.stdout.write(f'  → Ya existe: {especialidad}')
        
        # ========================================================================
        # 2. LABORATORIO (LIMS)
        # ========================================================================
        self.stdout.write('Creando Tipos de Muestra...')
        
        muestra_sangre, created = TipoMuestra.objects.get_or_create(
            codigo='SANGRE',
            defaults={
                'nombre': 'Sangre (Suero)',
                'color_tubo': 'Rojo',
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {muestra_sangre}'))
        else:
            self.stdout.write(f'  → Ya existe: {muestra_sangre}')
        
        muestra_orina, created = TipoMuestra.objects.get_or_create(
            codigo='ORINA',
            defaults={
                'nombre': 'Orina',
                'color_tubo': 'Frasco Estéril',
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {muestra_orina}'))
        else:
            self.stdout.write(f'  → Ya existe: {muestra_orina}')
        
        # Tipos de Examen
        self.stdout.write('Creando Tipos de Examen...')
        
        examenes_data = [
            {
                'codigo': 'HEMO',
                'nombre': 'Hemograma',
                'tipo_muestra': muestra_sangre,
                'precio': 150.00,
                'rango_referencia_texto': 'Ver valores individuales',
            },
            {
                'codigo': 'GLU',
                'nombre': 'Glucosa',
                'tipo_muestra': muestra_sangre,
                'precio': 100.00,
                'rango_referencia_texto': '70-100 mg/dL',
            },
            {
                'codigo': 'COL',
                'nombre': 'Colesterol Total',
                'tipo_muestra': muestra_sangre,
                'precio': 120.00,
                'rango_referencia_texto': '< 200 mg/dL',
            },
        ]
        
        for exam_data in examenes_data:
            tipo_muestra = exam_data.pop('tipo_muestra')
            examen, created = TipoExamen.objects.get_or_create(
                codigo=exam_data['codigo'],
                defaults={
                    **exam_data,
                    'tipo_muestra_requerida': tipo_muestra,
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {examen}'))
            else:
                self.stdout.write(f'  → Ya existe: {examen}')
        
        # ========================================================================
        # 3. USUARIOS DE PRUEBA
        # ========================================================================
        self.stdout.write('Creando Usuarios de Prueba...')
        
        # Admin (Superuser)
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'rol': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {admin_user.username} (password: admin123)'))
        else:
            self.stdout.write(f'  → Ya existe: {admin_user.username}')
        
        # Médico 1
        especialidad_cardio = Especialidad.objects.get(nombre='Cardiología')
        medico_user, created = User.objects.get_or_create(
            username='medico1',
            defaults={
                'email': 'medico1@example.com',
                'rol': 'medico',
                'first_name': 'Juan',
                'last_name': 'Médico',
                'is_staff': False,
            }
        )
        if created:
            medico_user.set_password('medico123')
            medico_user.save()
            # Crear el objeto Medico asociado
            medico_obj, medico_created = Medico.objects.get_or_create(
                user=medico_user,
                defaults={
                    'nombre': 'Juan',
                    'apellido': 'Médico',
                    'matricula': 'MAT-001',
                    'especialidad': especialidad_cardio,
                }
            )
            if medico_created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {medico_user.username} (password: medico123)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado usuario: {medico_user.username} (Medico ya existía)'))
        else:
            self.stdout.write(f'  → Ya existe: {medico_user.username}')
        
        # Paciente 1
        paciente_user, created = User.objects.get_or_create(
            username='paciente1',
            defaults={
                'email': 'paciente1@example.com',
                'rol': 'paciente',
                'first_name': 'María',
                'last_name': 'Paciente',
                'is_staff': False,
            }
        )
        if created:
            paciente_user.set_password('paciente123')
            paciente_user.save()
            # Crear el objeto Paciente asociado
            paciente_obj, paciente_created = Paciente.objects.get_or_create(
                user=paciente_user,
                defaults={
                    'nombre': 'María',
                    'apellido': 'Paciente',
                    'dni': '12345678',
                }
            )
            if paciente_created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {paciente_user.username} (password: paciente123)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado usuario: {paciente_user.username} (Paciente ya existía)'))
        else:
            self.stdout.write(f'  → Ya existe: {paciente_user.username}')
        
        # Operador laboratorio (rol formal `laboratorio`; LIMS, fuera del alcance IsEMRClinician)
        laboratorio_user, created = User.objects.get_or_create(
            username='laboratorio1',
            defaults={
                'email': 'laboratorio1@example.com',
                'rol': 'laboratorio',
                'first_name': 'Carlos',
                'last_name': 'Operador',
                'is_staff': True,
            }
        )
        if created:
            laboratorio_user.set_password('laboratorio123')
            laboratorio_user.save()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {laboratorio_user.username} (password: laboratorio123)'))
        else:
            self.stdout.write(f'  → Ya existe: {laboratorio_user.username}')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Seeding completado exitosamente!'))
        self.stdout.write(self.style.WARNING('\nUsuarios creados:'))
        self.stdout.write('  - admin / admin123 (Superuser)')
        self.stdout.write('  - medico1 / medico123 (Médico - Cardiología)')
        self.stdout.write('  - paciente1 / paciente123 (Paciente)')
        self.stdout.write('  - laboratorio1 / laboratorio123 (Operador laboratorio / LIMS)')



