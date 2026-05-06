"""
Tests para los modelos de la app solicitudes.
"""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, datetime
from solicitudes.models import Solicitud
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestSolicitudModel:
    """Tests para el modelo Solicitud."""
    
    @pytest.fixture
    def paciente_test(self):
        """Fixture para crear un paciente de prueba"""
        return Paciente.objects.create(
            dni='11111111',
            nombre='Juan',
            apellido='Pérez'
        )
    
    @pytest.fixture
    def medico_test(self):
        """Fixture para crear un médico de prueba"""
        especialidad = Especialidad.objects.create(nombre='Cardiología')
        return Medico.objects.create(
            matricula='MAT-001',
            nombre='Dr. Carlos',
            apellido='García',
            especialidad=especialidad
        )
    
    @pytest.fixture
    def usuario_test(self):
        """Fixture para crear un usuario de prueba"""
        return User.objects.create_user(
            username='medico_test',
            email='medico@test.com',
            password='testpass123',
            rol='medico'
        )
    
    def test_ciclo_vida_solicitud(self, paciente_test, medico_test, usuario_test):
        """
        Test Ciclo de Vida: Crea una solicitud PENDIENTE, cambia a COMPLETADA.
        """
        # Crear solicitud PENDIENTE
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Hemograma completo',
            estado='PENDIENTE',
            prioridad='NORMAL',
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Verificar estado inicial
        assert solicitud.estado == 'PENDIENTE'
        assert solicitud.fecha_completada is None
        assert solicitud.dias_pendiente >= 0
        
        # Cambiar a COMPLETADA
        solicitud.marcar_como_completada()
        
        # Verificar estado final
        assert solicitud.estado == 'COMPLETADA'
        assert solicitud.fecha_completada is not None
        assert solicitud.dias_pendiente == 0  # Ya no está pendiente
    
    def test_json_lims_tipos_examen(self, paciente_test, medico_test, usuario_test):
        """
        Test JSON: Guarda una lista de códigos ['HEMOGRAMA', 'GLUCOSA'] 
        en lims_tipos_examen y verifica que se recupere como lista.
        """
        # Crear solicitud con JSONField
        tipos_examen = ['HEMOGRAMA', 'GLUCOSA']
        paneles = ['PANEL_BASICO']
        
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Análisis de laboratorio',
            lims_tipos_examen=tipos_examen,
            lims_paneles=paneles,
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Verificar que se guardó como lista
        assert isinstance(solicitud.lims_tipos_examen, list)
        assert solicitud.lims_tipos_examen == tipos_examen
        assert solicitud.lims_tipos_examen[0] == 'HEMOGRAMA'
        assert solicitud.lims_tipos_examen[1] == 'GLUCOSA'
        
        # Verificar paneles también
        assert isinstance(solicitud.lims_paneles, list)
        assert solicitud.lims_paneles == paneles
        
        # Recuperar de la base de datos y verificar
        solicitud_refreshed = Solicitud.objects.get(id=solicitud.id)
        assert solicitud_refreshed.lims_tipos_examen == tipos_examen
        assert solicitud_refreshed.lims_paneles == paneles
    
    def test_validacion_fecha_limite_pasado(self, paciente_test, medico_test, usuario_test):
        """
        Test Validación Fecha: Intenta crear una solicitud con fecha_limite 
        en el pasado. Debe lanzar ValidationError.
        """
        # Crear solicitud con fecha_limite en el pasado
        fecha_pasado = timezone.now() - timedelta(days=1)
        
        solicitud = Solicitud(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test de validación',
            fecha_limite=fecha_pasado,
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Debe lanzar ValidationError al validar
        with pytest.raises(ValidationError) as exc_info:
            solicitud.full_clean()
        
        # Verificar que el error es sobre fecha_limite
        assert 'fecha_limite' in str(exc_info.value) or 'fecha límite' in str(exc_info.value).lower()
    
    def test_validacion_fecha_limite_igual_fecha_solicitud(self, paciente_test, medico_test, usuario_test):
        """
        Test Validación Fecha: Intenta crear una solicitud con fecha_limite 
        igual a fecha_solicitud. Debe lanzar ValidationError.
        """
        # Crear solicitud primero para tener fecha_solicitud
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test de validación',
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Intentar actualizar con fecha_limite igual a fecha_solicitud
        solicitud.fecha_limite = solicitud.fecha_solicitud
        
        # Debe lanzar ValidationError
        with pytest.raises(ValidationError) as exc_info:
            solicitud.full_clean()
        
        # Verificar que el error es sobre fecha_limite
        assert 'fecha_limite' in str(exc_info.value) or 'fecha límite' in str(exc_info.value).lower()
    
    def test_propiedades_dias_pendiente(self, paciente_test, medico_test, usuario_test):
        """
        Test Propiedades: Verifica que dias_pendiente calcule correctamente 
        la diferencia de días.
        """
        # Crear solicitud PENDIENTE
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test de días pendiente',
            estado='PENDIENTE',
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Obtener fecha_solicitud
        fecha_solicitud = solicitud.fecha_solicitud
        
        # Calcular días esperados
        dias_esperados = (timezone.now() - fecha_solicitud).days
        
        # Verificar que dias_pendiente calcule correctamente
        assert solicitud.dias_pendiente == dias_esperados
        assert solicitud.dias_pendiente >= 0
        
        # Cambiar a COMPLETADA y verificar que dias_pendiente sea 0
        solicitud.estado = 'COMPLETADA'
        solicitud.save()
        
        assert solicitud.dias_pendiente == 0
    
    def test_propiedad_esta_vencida(self, paciente_test, medico_test, usuario_test):
        """
        Test Propiedad esta_vencida: Verifica que calcule correctamente 
        si una solicitud está vencida.
        """
        # Crear solicitud con fecha_limite en el futuro
        fecha_futuro = timezone.now() + timedelta(days=7)
        solicitud_futuro = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test vencida - futuro',
            estado='PENDIENTE',
            fecha_limite=fecha_futuro,
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # No debe estar vencida
        assert solicitud_futuro.esta_vencida is False
        
        # Crear solicitud con fecha_limite en el pasado
        fecha_pasado = timezone.now() - timedelta(days=1)
        solicitud_pasado = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test vencida - pasado',
            estado='PENDIENTE',
            fecha_limite=fecha_pasado,
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Debe estar vencida
        assert solicitud_pasado.esta_vencida is True
        
        # Si está COMPLETADA, no debe estar vencida aunque tenga fecha_limite pasada
        solicitud_pasado.estado = 'COMPLETADA'
        solicitud_pasado.save()
        assert solicitud_pasado.esta_vencida is False
        
        # Si está CANCELADA, no debe estar vencida
        solicitud_pasado.estado = 'CANCELADA'
        solicitud_pasado.save()
        assert solicitud_pasado.esta_vencida is False
    
    def test_solicitud_sin_fecha_limite(self, paciente_test, medico_test, usuario_test):
        """
        Test que una solicitud sin fecha_limite no está vencida.
        """
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test sin fecha límite',
            estado='PENDIENTE',
            fecha_limite=None,
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # No debe estar vencida si no tiene fecha_limite
        assert solicitud.esta_vencida is False
    
    def test_relaciones_solicitud(self, paciente_test, medico_test, usuario_test):
        """
        Test que las relaciones de Solicitud funcionan correctamente.
        """
        # Crear segundo médico para ManyToMany
        especialidad2 = Especialidad.objects.create(nombre='Neurología')
        medico2 = Medico.objects.create(
            matricula='MAT-002',
            nombre='Dr. Ana',
            apellido='Rodríguez',
            especialidad=especialidad2
        )
        
        # Crear solicitud
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='CONSULTA_ESPECIALISTA',
            descripcion='Consulta con especialista',
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        # Agregar médicos asignados
        solicitud.medicos_asignados.add(medico2)
        
        # Verificar relaciones
        assert solicitud.paciente == paciente_test
        assert solicitud.medico_solicitante == medico_test
        assert medico2 in solicitud.medicos_asignados.all()
        assert solicitud.creado_por == usuario_test
        assert solicitud.modificado_por == usuario_test
    
    def test_solicitud_cascade_al_borrar_paciente(self, paciente_test, medico_test, usuario_test):
        """
        Test Integridad: Verifica que al borrar un Paciente,
        sus solicitudes también se borren (CASCADE).
        """
        # Crear solicitud
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test CASCADE',
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        solicitud_id = solicitud.id
        
        # Borrar el paciente
        paciente_test.delete()
        
        # Verificar que la solicitud también se borró (CASCADE)
        assert not Solicitud.objects.filter(id=solicitud_id).exists()
    
    def test_solicitud_set_null_al_borrar_medico(self, paciente_test, medico_test, usuario_test):
        """
        Test Integridad: Verifica que al borrar un Médico,
        el campo medico_solicitante pase a NULL (SET_NULL).
        """
        # Crear solicitud
        solicitud = Solicitud.objects.create(
            paciente=paciente_test,
            medico_solicitante=medico_test,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Test SET_NULL',
            creado_por=usuario_test,
            modificado_por=usuario_test
        )
        
        assert solicitud.medico_solicitante == medico_test
        
        # Borrar el médico
        medico_test.delete()
        
        # Refrescar la solicitud
        solicitud.refresh_from_db()
        
        # Verificar que medico_solicitante es NULL
        assert solicitud.medico_solicitante is None
        # Verificar que la solicitud sigue existiendo
        assert Solicitud.objects.filter(id=solicitud.id).exists()



