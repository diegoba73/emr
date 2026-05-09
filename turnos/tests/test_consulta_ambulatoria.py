"""
Tests para el endpoint de registro de consulta ambulatoria.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from turnos.models import Atencion, ConsultaAmbulatoria, Turno, Recurso
from pacientes.models import Paciente
from medicos.models import Medico
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ConsultaAmbulatoriaTestCase(TestCase):
    """
    Tests para el endpoint registrar_consulta de AtencionViewSet.
    """
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = APIClient()
        
        # Crear usuarios
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Crear médico
        self.medico_user = User.objects.create_user(
            username='medico1',
            email='medico1@test.com',
            password='testpass123',
            first_name='Juan',
            last_name='Médico',
            rol='medico'
        )
        self.medico = Medico.objects.create(
            user=self.medico_user,
            nombre='Juan',
            apellido='Médico',
            matricula='12345'
        )
        self.medico_user.medico = self.medico
        self.medico_user.save()
        
        # Crear otro médico (para pruebas de permisos)
        self.medico2_user = User.objects.create_user(
            username='medico2',
            email='medico2@test.com',
            password='testpass123',
            first_name='Pedro',
            last_name='Médico2',
            rol='medico'
        )
        self.medico2 = Medico.objects.create(
            user=self.medico2_user,
            nombre='Pedro',
            apellido='Médico2',
            matricula='67890'
        )
        self.medico2_user.medico = self.medico2
        self.medico2_user.save()
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            nombre='Paciente',
            apellido='Test',
            dni='12345678',
            fecha_nacimiento='1990-01-01'
        )
        
        # Crear recurso (consultorio)
        self.recurso = Recurso.objects.create(
            nombre='Consultorio 1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True
        )
        
        # Crear turno
        self.turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=timezone.now(),
            fecha_hora_fin=timezone.now() + timedelta(hours=1),
            estado=Turno.Estado.CONFIRMADO
        )
        
        # Crear atención
        self.atencion = Atencion.objects.create(
            turno=self.turno,
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
            estado_clinico=Atencion.EstadoClinico.ABIERTA
        )
    
    def test_registrar_consulta_exitoso(self):
        """
        Test: Crear consulta ambulatoria exitosamente.
        Verifica que se crea el registro en DB.
        """
        self.client.force_authenticate(user=self.medico_user)
        
        datos_consulta = {
            'anamnesis': 'Paciente refiere dolor de cabeza desde hace 3 días.',
            'examen_fisico': 'Paciente en buen estado general. Sin signos de alarma.',
            'diagnostico_presuntivo': 'Cefalea tensional',
            'plan_manejo': 'Reposo, analgésicos, control en 7 días.'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')
        
        # Verificar respuesta
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('anamnesis', response.data)
        self.assertEqual(response.data['anamnesis'], datos_consulta['anamnesis'])
        
        # Verificar que se creó en la base de datos
        consulta = ConsultaAmbulatoria.objects.get(atencion=self.atencion)
        self.assertEqual(consulta.anamnesis, datos_consulta['anamnesis'])
        self.assertEqual(consulta.examen_fisico, datos_consulta['examen_fisico'])
        self.assertEqual(consulta.diagnostico_presuntivo, datos_consulta['diagnostico_presuntivo'])
        self.assertEqual(consulta.plan_manejo, datos_consulta['plan_manejo'])
    
    def test_registrar_consulta_duplicada(self):
        """
        Test: Enviar datos dos veces, verifica que actualiza en vez de romper.
        """
        self.client.force_authenticate(user=self.medico_user)
        
        # Primera creación
        datos_iniciales = {
            'anamnesis': 'Anamnesis inicial',
            'examen_fisico': 'Examen inicial'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response1 = self.client.post(url, datos_iniciales, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Verificar que existe
        consulta = ConsultaAmbulatoria.objects.get(atencion=self.atencion)
        self.assertEqual(consulta.anamnesis, 'Anamnesis inicial')
        
        # Segunda actualización
        datos_actualizados = {
            'anamnesis': 'Anamnesis actualizada',
            'examen_fisico': 'Examen actualizado',
            'diagnostico_presuntivo': 'Nuevo diagnóstico'
        }
        
        response2 = self.client.post(url, datos_actualizados, format='json')
        
        # Verificar que actualiza (status 200) en vez de crear otro
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verificar que se actualizó en la base de datos
        consulta.refresh_from_db()
        self.assertEqual(consulta.anamnesis, 'Anamnesis actualizada')
        self.assertEqual(consulta.examen_fisico, 'Examen actualizado')
        self.assertEqual(consulta.diagnostico_presuntivo, 'Nuevo diagnóstico')
        
        # Verificar que solo existe una consulta
        count = ConsultaAmbulatoria.objects.filter(atencion=self.atencion).count()
        self.assertEqual(count, 1)
    
    def test_permiso_denegado(self):
        """Un médico que NO es el ``medico_principal`` no puede ver la atención.

        ``AtencionViewSet.get_queryset`` filtra por ``medico_principal=user.medico``;
        para un médico distinto, el detalle devuelve 404 (decisión deliberada
        para no leakear la existencia de atenciones de otros médicos).
        """
        self.client.force_authenticate(user=self.medico2_user)

        datos_consulta = {'anamnesis': 'Intento de acceso no autorizado'}
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.assertRaises(ConsultaAmbulatoria.DoesNotExist):
            ConsultaAmbulatoria.objects.get(atencion=self.atencion)
    
    def test_admin_puede_registrar(self):
        """
        Test: Admin puede registrar consulta para cualquier atención.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        datos_consulta = {
            'anamnesis': 'Consulta registrada por admin',
            'examen_fisico': 'Examen realizado'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')
        
        # Verificar que admin puede registrar
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar que se creó
        consulta = ConsultaAmbulatoria.objects.get(atencion=self.atencion)
        self.assertEqual(consulta.anamnesis, 'Consulta registrada por admin')
    
    def test_anamnesis_obligatoria_si_finalizada(self):
        """
        Test: Si el estado de la atención es FINALIZADA, anamnesis es obligatoria.
        """
        self.client.force_authenticate(user=self.medico_user)
        
        # Marcar atención como FINALIZADA
        self.atencion.estado_clinico = Atencion.EstadoClinico.FINALIZADA
        self.atencion.save()
        
        # Intentar registrar sin anamnesis
        datos_consulta = {
            'examen_fisico': 'Examen sin anamnesis',
            'estado_clinico': 'FINALIZADA'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')
        
        # Verificar que se rechaza
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('anamnesis', response.data)
        
        # Verificar que NO se creó la consulta
        with self.assertRaises(ConsultaAmbulatoria.DoesNotExist):
            ConsultaAmbulatoria.objects.get(atencion=self.atencion)
    
    def test_no_editar_atencion_cerrada(self):
        """
        Test: No se puede editar una consulta de una atención ya cerrada (fecha_cierre != None).
        """
        self.client.force_authenticate(user=self.medico_user)
        
        # Cerrar la atención
        self.atencion.fecha_cierre = timezone.now()
        self.atencion.estado_clinico = Atencion.EstadoClinico.FINALIZADA
        self.atencion.save()
        
        datos_consulta = {
            'anamnesis': 'Intento de editar atención cerrada'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')
        
        # Verificar que se rechaza con 409 CONFLICT
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.data)
    
    def test_actualizar_estado_atencion(self):
        """
        Test: Al registrar consulta, se puede actualizar el estado de la atención.
        """
        self.client.force_authenticate(user=self.medico_user)
        
        datos_consulta = {
            'anamnesis': 'Consulta completa',
            'examen_fisico': 'Examen completo',
            'estado_clinico': 'EN_REVISION'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')
        
        # Verificar que se creó la consulta
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar que se actualizó el estado de la atención
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.estado_clinico, Atencion.EstadoClinico.EN_REVISION)
    
    def test_tipo_intervencion_incorrecto(self):
        """
        Test: No se puede crear consulta ambulatoria en atención que no sea tipo CONSULTA.
        """
        self.client.force_authenticate(user=self.medico_user)
        
        # Cambiar tipo de intervención
        self.atencion.tipo_intervencion = Atencion.TipoIntervencion.CIRUGIA
        self.atencion.save()
        
        datos_consulta = {
            'anamnesis': 'Intento en atención de cirugía'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_consulta, format='json')
        
        # Verificar que se rechaza
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_campos_completos_consulta(self):
        """
        Test: Verificar que todos los campos de la consulta se guardan correctamente.
        """
        self.client.force_authenticate(user=self.medico_user)
        
        datos_completos = {
            'anamnesis': 'Anamnesis completa',
            'examen_fisico': 'Examen físico completo',
            'diagnostico_presuntivo': 'Diagnóstico presuntivo',
            'plan_manejo': 'Plan de manejo detallado',
            'antecedentes_relevantes': 'Antecedentes del paciente',
            'alergias': 'Ninguna alergia conocida',
            'medicacion_actual': 'Paracetamol 500mg',
            'diagnostico_definitivo': 'Diagnóstico definitivo',
            'observaciones_medicas': 'Observaciones adicionales'
        }
        
        url = f'/api/atenciones/{self.atencion.id}/registrar-consulta/'
        response = self.client.post(url, datos_completos, format='json')
        
        # Verificar respuesta
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar todos los campos en la base de datos
        consulta = ConsultaAmbulatoria.objects.get(atencion=self.atencion)
        self.assertEqual(consulta.anamnesis, datos_completos['anamnesis'])
        self.assertEqual(consulta.examen_fisico, datos_completos['examen_fisico'])
        self.assertEqual(consulta.diagnostico_presuntivo, datos_completos['diagnostico_presuntivo'])
        self.assertEqual(consulta.plan_manejo, datos_completos['plan_manejo'])
        self.assertEqual(consulta.antecedentes_relevantes, datos_completos['antecedentes_relevantes'])
        self.assertEqual(consulta.alergias, datos_completos['alergias'])
        self.assertEqual(consulta.medicacion_actual, datos_completos['medicacion_actual'])
        self.assertEqual(consulta.diagnostico_definitivo, datos_completos['diagnostico_definitivo'])
        self.assertEqual(consulta.observaciones_medicas, datos_completos['observaciones_medicas'])









