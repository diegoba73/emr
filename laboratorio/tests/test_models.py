"""
Tests para los modelos de la app laboratorio.
"""
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from laboratorio.models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
)
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestSolicitudExamenModel:
    """Tests para el modelo SolicitudExamen."""
    
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
        especialidad = Especialidad.objects.create(
            nombre=f'Cardiología {uuid.uuid4().hex[:12]}'
        )
        return Medico.objects.create(
            matricula='MAT-001',
            nombre='Dr. Carlos',
            apellido='García',
            especialidad=especialidad
        )
    
    @pytest.fixture
    def tipo_muestra_sangre(self):
        """Fixture para crear un tipo de muestra"""
        return TipoMuestra.objects.create(
            codigo='SANGRE',
            nombre='Sangre',
            color_tubo='Rojo',
            activo=True
        )
    
    @pytest.fixture
    def tipo_examen_glucosa(self, tipo_muestra_sangre):
        """Fixture para crear un tipo de examen"""
        return TipoExamen.objects.create(
            codigo='GLU',
            nombre='Glucosa',
            abreviatura='GLU',
            tipo_muestra_requerida=tipo_muestra_sangre,
            precio=150.00,
            rango_referencia_texto='70-100 mg/dL',
            activo=True
        )
    
    def test_flujo_papel_medico_externo(self, paciente_test, tipo_examen_glucosa):
        """
        Test Flujo Papel: Crea una solicitud para un paciente existente 
        pero con un médico externo (texto libre). Debe guardarse correctamente.
        """
        # Crear solicitud con médico externo
        solicitud = SolicitudExamen.objects.create(
            paciente=paciente_test,
            medico_externo_nombre='Dr. Juan Pérez (Externo)',
            origen_solicitud='EXTERNO_CEHTA',
            estado='PENDIENTE'
        )
        
        # Agregar examen
        solicitud.tipos_examen.add(tipo_examen_glucosa)
        
        # Verificar que se guardó correctamente
        assert solicitud.paciente == paciente_test
        assert solicitud.medico_externo_nombre == 'Dr. Juan Pérez (Externo)'
        assert solicitud.medico_interno is None
        assert solicitud.origen_solicitud == 'EXTERNO_CEHTA'
        assert solicitud.numero is not None
        assert solicitud.numero.startswith('LAB-')
        assert tipo_examen_glucosa in solicitud.tipos_examen.all()
    
    def test_flujo_digital_medico_interno(self, paciente_test, medico_test, tipo_examen_glucosa):
        """
        Test Flujo Digital: Crea una solicitud vinculada a un medico_interno.
        """
        # Crear solicitud con médico interno
        solicitud = SolicitudExamen.objects.create(
            paciente=paciente_test,
            medico_interno=medico_test,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='PENDIENTE'
        )
        
        # Agregar examen
        solicitud.tipos_examen.add(tipo_examen_glucosa)
        
        # Verificar que se guardó correctamente
        assert solicitud.paciente == paciente_test
        assert solicitud.medico_interno == medico_test
        assert solicitud.medico_externo_nombre is None or solicitud.medico_externo_nombre == ''
        assert solicitud.origen_solicitud == 'AMBULATORIO_CEHTA'
        assert solicitud.numero is not None
        assert solicitud.numero.startswith('LAB-')
        assert tipo_examen_glucosa in solicitud.tipos_examen.all()
    
    def test_numeracion_protocolo_unico(self, paciente_test, tipo_examen_glucosa):
        """
        Test Numeración: Crea dos solicitudes y verifica que el número 
        de protocolo se incremente o sea único.
        """
        # Crear primera solicitud
        solicitud1 = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='PENDIENTE'
        )
        solicitud1.tipos_examen.add(tipo_examen_glucosa)
        
        # Verificar que tiene número
        assert solicitud1.numero is not None
        assert solicitud1.numero.startswith('LAB-')
        
        # Crear segunda solicitud
        solicitud2 = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='PENDIENTE'
        )
        solicitud2.tipos_examen.add(tipo_examen_glucosa)
        
        # Verificar que tiene número diferente
        assert solicitud2.numero is not None
        assert solicitud2.numero.startswith('LAB-')
        assert solicitud2.numero != solicitud1.numero
        
        # Verificar que los números son únicos
        assert SolicitudExamen.objects.filter(numero=solicitud1.numero).count() == 1
        assert SolicitudExamen.objects.filter(numero=solicitud2.numero).count() == 1
    
    def test_integridad_tipo_examen_protect(self, paciente_test, tipo_examen_glucosa):
        """
        Test Integridad: Verifica que al borrar un TipoExamen, 
        no se borren los resultados históricos (PROTECT).
        """
        # Crear solicitud y resultado
        solicitud = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='EN_PROCESO'
        )
        solicitud.tipos_examen.add(tipo_examen_glucosa)
        
        usuario = User.objects.create_user(
            username='validador',
            email='validador@test.com',
            password='testpass123',
            rol='medico'
        )
        
        resultado = ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=tipo_examen_glucosa,
            valor_obtenido='95.5',
            es_patologico=False,
            validado_por=usuario
        )
        
        resultado_id = resultado.id
        
        # Intentar borrar el tipo de examen debe fallar (PROTECT)
        with pytest.raises((ValidationError, Exception)) as exc_info:
            tipo_examen_glucosa.delete()
        
        # Verificar que el resultado sigue existiendo
        assert ResultadoExamen.objects.filter(id=resultado_id).exists()
        assert tipo_examen_glucosa.id is not None  # El tipo de examen no se borró
    
    def test_finalizar_solicitud_con_resultados_vacios_persiste(self, paciente_test, tipo_muestra_sangre):
        """
        Una orden con ResultadoExamen autogenerado vacío puede pasar a FINALIZADO
        (regresión: SolicitudExamen.clean no debe impedirlo a nivel modelo).
        """
        tipo = TipoExamen.objects.create(
            codigo='GLU-FIN-CLEAN',
            nombre='Glucosa',
            tipo_muestra_requerida=tipo_muestra_sangre,
            precio=1.0,
            activo=True,
        )
        solicitud = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='PENDIENTE',
        )
        solicitud.tipos_examen.add(tipo)
        ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=tipo,
            valor_obtenido='',
        )
        solicitud.estado = 'FINALIZADO'
        solicitud.save(update_fields=['estado'])
        solicitud.refresh_from_db()
        assert solicitud.estado == 'FINALIZADO'

    def test_resultado_no_cargar_solicitud_finalizada(self, paciente_test, tipo_examen_glucosa):
        """
        Test Validación: Un resultado no puede cargarse si la solicitud está finalizada.
        """
        solicitud = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='FINALIZADO'
        )
        
        usuario = User.objects.create_user(
            username='validador2',
            email='validador2@test.com',
            password='testpass123',
            rol='medico'
        )
        
        # Intentar crear resultado debe fallar
        with pytest.raises(ValidationError) as exc_info:
            ResultadoExamen.objects.create(
                solicitud=solicitud,
                tipo_examen=tipo_examen_glucosa,
                valor_obtenido='95.5',
                es_patologico=False,
                validado_por=usuario
            )
        
        assert 'finalizada' in str(exc_info.value).lower()
    
    def test_propiedad_medico_display(self, paciente_test, medico_test):
        """
        Test de la propiedad medico_display.
        """
        # Test con médico interno
        solicitud_interno = SolicitudExamen.objects.create(
            paciente=paciente_test,
            medico_interno=medico_test,
            origen_solicitud='AMBULATORIO_CEHTA'
        )
        assert solicitud_interno.medico_display == medico_test.nombre_completo
        
        # Test con médico externo
        solicitud_externo = SolicitudExamen.objects.create(
            paciente=paciente_test,
            medico_externo_nombre='Dr. Externo',
            origen_solicitud='EXTERNO_ICPL'
        )
        assert solicitud_externo.medico_display == 'Dr. Externo'
        
        # Test sin médico
        solicitud_sin_medico = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='GUARDIA'
        )
        assert solicitud_sin_medico.medico_display == "Sin médico asignado"
    
    def test_panel_examen_con_tipos_examen(self, tipo_muestra_sangre):
        """
        Test que un PanelExamen puede tener múltiples TipoExamen.
        """
        # Crear tipos de examen
        tipo1 = TipoExamen.objects.create(
            codigo='GLU',
            nombre='Glucosa',
            tipo_muestra_requerida=tipo_muestra_sangre,
            precio=150.00
        )
        tipo2 = TipoExamen.objects.create(
            codigo='HGB',
            nombre='Hemoglobina',
            tipo_muestra_requerida=tipo_muestra_sangre,
            precio=200.00
        )
        
        # Crear panel
        panel = PanelExamen.objects.create(
            codigo='HEMOGRAMA',
            nombre='Hemograma Completo'
        )
        
        # Agregar tipos de examen al panel
        panel.tipos_examen.add(tipo1, tipo2)
        
        # Verificar
        assert panel.tipos_examen.count() == 2
        assert tipo1 in panel.tipos_examen.all()
        assert tipo2 in panel.tipos_examen.all()
    
    def test_solicitud_con_paneles(self, paciente_test, tipo_muestra_sangre):
        """
        Test que una SolicitudExamen puede tener paneles.
        """
        # Crear tipos de examen
        tipo1 = TipoExamen.objects.create(
            codigo='GLU',
            nombre='Glucosa',
            tipo_muestra_requerida=tipo_muestra_sangre,
            precio=150.00
        )
        
        # Crear panel
        panel = PanelExamen.objects.create(
            codigo='HEMOGRAMA',
            nombre='Hemograma Completo'
        )
        panel.tipos_examen.add(tipo1)
        
        # Crear solicitud con panel
        solicitud = SolicitudExamen.objects.create(
            paciente=paciente_test,
            origen_solicitud='AMBULATORIO_CEHTA'
        )
        solicitud.paneles.add(panel)
        
        # Verificar
        assert panel in solicitud.paneles.all()
        assert solicitud.paneles.count() == 1



