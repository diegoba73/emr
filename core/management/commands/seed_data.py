"""
Comando de gestión Django para poblar la base de datos con datos iniciales.
Idempotente: usa get_or_create para no duplicar datos si se corre dos veces.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from catalogos.models import CentroFisico, TipoAtencion
from medicos.models import Especialidad, Medico
from laboratorio.models import TipoMuestra, TipoExamen, SolicitudExamen, ResultadoExamen
from laboratorio.models_catalog import Muestra
from pacientes.models import Paciente
from turnos.models import Turno, Atencion, Recurso

User = get_user_model()

# Claves estables para datos QA demo (desarrollo/staging; no PHI real).
QA_TURNO_MOTIVO = 'QA DEMO TURNO MEDICO1-PACIENTE1'
QA_LIMS_NUMERO = 'LAB-DEMO-QA-00001'
QA_MUESTRA_CODIGO = 'MUE-DEMO-QA-00001'
QA_PACIENTE_AJENO_DNI = 'QA-DEMO-AJENO-01'
QA_RECURSO_NOMBRE = 'QA DEMO Consultorio 1'


class Command(BaseCommand):
    """Comando Django para poblar datos iniciales."""
    
    help = 'Pobla la base de datos con datos iniciales (idempotente)'
    
    def _ensure_user(self, username, password, defaults):
        """Crea usuario demo si no existe; no resetea contraseña en corridas posteriores."""
        user, created = User.objects.get_or_create(username=username, defaults=defaults)
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {username} (password: {password})'))
        else:
            self.stdout.write(f'  → Ya existe: {username}')
        return user, created

    def _seed_qa_demo_emr_lims(
        self,
        medico_obj,
        paciente_uno,
        tipo_glu,
        muestra_sangre,
    ):
        """Datos sintéticos mínimos para smoke QA por rol (idempotente)."""
        self.stdout.write('Creando datos demo QA (EMR + LIMS)...')

        paciente_ajeno, created = Paciente.objects.get_or_create(
            dni=QA_PACIENTE_AJENO_DNI,
            defaults={
                'nombre': 'Paciente Demo',
                'apellido': 'Ajeno',
                'observaciones': 'QA DEMO - paciente ajeno para pruebas de aislamiento',
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Paciente ajeno demo: {paciente_ajeno.dni}'))
        else:
            self.stdout.write(f'  → Ya existe paciente ajeno: {paciente_ajeno.dni}')

        recurso_demo, recurso_created = Recurso.objects.get_or_create(
            nombre=QA_RECURSO_NOMBRE,
            defaults={
                'ubicacion': Recurso.Ubicacion.ICPL,
                'tipo_recurso': Recurso.TipoRecurso.CONSULTORIO,
                'activo': True,
            },
        )
        if recurso_created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Recurso demo QA: {recurso_demo.nombre}'))
        else:
            self.stdout.write(f'  → Ya existe recurso demo QA: {recurso_demo.nombre}')

        turno = Turno.objects.filter(motivo_reserva=QA_TURNO_MOTIVO).first()
        if not turno:
            inicio = timezone.now() + timedelta(days=7)
            fin = inicio + timedelta(minutes=30)
            turno = Turno.objects.create(
                paciente=paciente_uno,
                medico=medico_obj,
                recurso=recurso_demo,
                fecha_hora_inicio=inicio,
                fecha_hora_fin=fin,
                estado=Turno.Estado.CONFIRMADO,
                motivo_reserva=QA_TURNO_MOTIVO,
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Turno demo QA #{turno.id}'))
        else:
            if turno.recurso_id is None:
                turno.recurso = recurso_demo
                turno.save(update_fields=['recurso'])
                self.stdout.write(self.style.SUCCESS(f'  ✓ Turno demo QA #{turno.id} vinculado a recurso'))
            else:
                self.stdout.write(f'  → Ya existe turno demo QA #{turno.id}')

        atencion = Atencion.objects.filter(turno=turno).first()
        if not atencion:
            atencion = Atencion.objects.create(
                turno=turno,
                paciente=paciente_uno,
                medico_principal=medico_obj,
                tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
                tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
                estado_clinico=Atencion.EstadoClinico.ABIERTA,
                observaciones_generales='QA DEMO - atención sintética para smoke',
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Atención demo QA #{atencion.id}'))
        else:
            self.stdout.write(f'  → Ya existe atención demo QA #{atencion.id}')

        solicitud, created = SolicitudExamen.objects.get_or_create(
            numero=QA_LIMS_NUMERO,
            defaults={
                'paciente': paciente_uno,
                'medico_interno': medico_obj,
                'origen_solicitud': 'AMBULATORIO_CEHTA',
                'estado': 'EN_PROCESO',
                'observaciones': 'QA DEMO - orden LIMS sintética para smoke',
            },
        )
        if not solicitud.tipos_examen.filter(pk=tipo_glu.pk).exists():
            solicitud.tipos_examen.add(tipo_glu)
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Orden LIMS demo: {solicitud.numero}'))
        else:
            self.stdout.write(f'  → Ya existe orden LIMS demo: {solicitud.numero}')

        resultado, res_created = ResultadoExamen.objects.get_or_create(
            solicitud=solicitud,
            tipo_examen=tipo_glu,
            defaults={
                'valor_obtenido': 'Resultado demo no clínico',
                'es_patologico': False,
            },
        )
        if not res_created and not resultado.valor_obtenido:
            resultado.valor_obtenido = 'Resultado demo no clínico'
            resultado.save(update_fields=['valor_obtenido'])
        if res_created:
            self.stdout.write(self.style.SUCCESS('  ✓ Resultado LIMS demo (no validado)'))
        else:
            self.stdout.write('  → Ya existe resultado LIMS demo')

        muestra, muestra_created = Muestra.objects.get_or_create(
            codigo_barra=QA_MUESTRA_CODIGO,
            defaults={
                'solicitud': solicitud,
                'paciente': paciente_uno,
                'tipo_muestra': muestra_sangre,
                'estado': 'TOMADA',
                'observaciones': 'QA DEMO - Muestra Demo',
            },
        )
        if muestra_created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Muestra LIMS demo: {muestra.codigo_barra}'))
        else:
            self.stdout.write(f'  → Ya existe muestra LIMS demo: {muestra.codigo_barra}')

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

        # Recursos agendables (consultorios) — requeridos para crear turnos en la UI
        self.stdout.write('Creando Recursos (consultorios)...')

        recursos_infra = [
            {
                'nombre': 'Consultorio CEHTA 1',
                'ubicacion': Recurso.Ubicacion.CEHTA,
                'tipo_recurso': Recurso.TipoRecurso.CONSULTORIO,
            },
            {
                'nombre': 'Consultorio ICPL 1',
                'ubicacion': Recurso.Ubicacion.ICPL,
                'tipo_recurso': Recurso.TipoRecurso.CONSULTORIO,
            },
        ]
        for recurso_data in recursos_infra:
            recurso, created = Recurso.objects.get_or_create(
                nombre=recurso_data['nombre'],
                defaults={
                    'ubicacion': recurso_data['ubicacion'],
                    'tipo_recurso': recurso_data['tipo_recurso'],
                    'activo': True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {recurso}'))
            else:
                self.stdout.write(f'  → Ya existe: {recurso}')

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

        tipo_glu = TipoExamen.objects.get(codigo='GLU')
        
        # ========================================================================
        # 3. USUARIOS DE PRUEBA
        # ========================================================================
        self.stdout.write('Creando Usuarios de Prueba...')
        
        admin_user, _ = self._ensure_user(
            'admin',
            'admin123',
            {
                'email': 'admin@example.com',
                'rol': 'admin',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        
        especialidad_cardio = Especialidad.objects.get(nombre='Cardiología')
        medico_user, _ = self._ensure_user(
            'medico1',
            'medico123',
            {
                'email': 'medico1@example.com',
                'rol': 'medico',
                'first_name': 'Juan',
                'last_name': 'Médico',
                'is_staff': False,
            },
        )
        medico_obj, medico_created = Medico.objects.get_or_create(
            user=medico_user,
            defaults={
                'nombre': 'Juan',
                'apellido': 'Médico',
                'matricula': 'MAT-001',
                'especialidad': especialidad_cardio,
            },
        )
        if medico_created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Perfil médico: {medico_user.username}'))

        paciente_user, _ = self._ensure_user(
            'paciente1',
            'paciente123',
            {
                'email': 'paciente1@example.com',
                'rol': 'paciente',
                'first_name': 'Paciente',
                'last_name': 'Demo Uno',
                'is_staff': False,
            },
        )
        paciente_uno, paciente_created = Paciente.objects.get_or_create(
            user=paciente_user,
            defaults={
                'nombre': 'Paciente Demo',
                'apellido': 'Uno',
                'dni': 'QA-DEMO-00001',
                'observaciones': 'QA DEMO - paciente propio portal paciente1',
            },
        )
        if not paciente_created:
            Paciente.objects.filter(pk=paciente_uno.pk).update(
                nombre='Paciente Demo',
                apellido='Uno',
            )
            paciente_uno.refresh_from_db()
        if paciente_created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Ficha paciente demo: {paciente_user.username}'))
        
        laboratorio_user, _ = self._ensure_user(
            'laboratorio1',
            'laboratorio123',
            {
                'email': 'laboratorio1@example.com',
                'rol': 'laboratorio',
                'first_name': 'Carlos',
                'last_name': 'Operador',
                'is_staff': True,
            },
        )

        enfermeria_user, _ = self._ensure_user(
            'enfermeria1',
            'enfermeria123',
            {
                'email': 'enfermeria1@example.com',
                'rol': 'enfermeria',
                'first_name': 'Ana',
                'last_name': 'Enfermera',
                'is_staff': False,
            },
        )

        secretaria_user, _ = self._ensure_user(
            'secretaria1',
            'secretaria123',
            {
                'email': 'secretaria1@example.com',
                'rol': 'secretaria',
                'first_name': 'Laura',
                'last_name': 'Secretaria',
                'is_staff': False,
            },
        )

        # ========================================================================
        # 4. DATOS DEMO QA (EMR + LIMS)
        # ========================================================================
        self._seed_qa_demo_emr_lims(
            medico_obj=medico_obj,
            paciente_uno=paciente_uno,
            tipo_glu=tipo_glu,
            muestra_sangre=muestra_sangre,
        )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Seeding completado exitosamente!'))
        self.stdout.write(self.style.WARNING('\nUsuarios demo (solo desarrollo):'))
        self.stdout.write('  - admin / admin123 (Superuser)')
        self.stdout.write('  - medico1 / medico123 (Médico - Cardiología)')
        self.stdout.write('  - paciente1 / paciente123 (Paciente Demo Uno)')
        self.stdout.write('  - laboratorio1 / laboratorio123 (Operador laboratorio / LIMS)')
        self.stdout.write('  - enfermeria1 / enfermeria123 (Enfermería)')
        self.stdout.write('  - secretaria1 / secretaria123 (Secretaría)')
        self.stdout.write(self.style.WARNING('\nDatos QA sintéticos:'))
        self.stdout.write(f'  - Paciente ajeno DNI {QA_PACIENTE_AJENO_DNI}')
        self.stdout.write(f'  - Turno demo ({QA_TURNO_MOTIVO})')
        self.stdout.write(f'  - Orden LIMS {QA_LIMS_NUMERO} + muestra {QA_MUESTRA_CODIGO}')
        self.stdout.write(self.style.WARNING('\nReejecutar: python manage.py seed_data (idempotente)'))



