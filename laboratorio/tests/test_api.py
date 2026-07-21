"""
Tests de integración API para la app laboratorio (LIMS).
"""
import pytest
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from laboratorio.models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
)
from laboratorio.models_catalog import Muestra
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from auditoria.models import AuditEvent

User = get_user_model()


@pytest.mark.django_db
class TestSolicitudExamenAPI(APITestCase):
    """Tests de integración para la API de Solicitudes de Examen."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        # Crear usuario de laboratorio
        self.user_lab = User.objects.create_user(
            username='lab_user',
            email='lab@test.com',
            password='testpass123',
            rol='laboratorio',
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username='lims_admin',
            email='lims-admin@test.com',
            password='adminpass123',
            rol='admin',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user_lab)
        
        # Códigos con prefijo para no colisionar con TestLimsAuthorization (unique en BD)
        _p = 'TSEA'
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f'SNG{_p}',
            nombre='Sangre',
            color_tubo='Rojo',
            activo=True
        )
        
        self.tipo_examen_1 = TipoExamen.objects.create(
            codigo=f'GLU{_p}',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=100.00,
            rango_referencia_texto='70-100 mg/dL',
            activo=True
        )
        
        self.tipo_examen_2 = TipoExamen.objects.create(
            codigo=f'HEM{_p}',
            nombre='Hemoglobina',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=150.00,
            rango_referencia_texto='12-16 g/dL',
            activo=True
        )
        
        self.panel = PanelExamen.objects.create(
            codigo=f'HCOMP{_p}',
            nombre='Hemograma Completo',
            activo=True
        )
        self.panel.tipos_examen.add(self.tipo_examen_2)
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            dni='12345678',
            nombre='Juan',
            apellido='Pérez'
        )
        
        self.especialidad = Especialidad.objects.create(nombre=f'Cardiología {_p}')
        self.medico = Medico.objects.create(
            nombre='Dr. Test',
            apellido='Médico',
            matricula=f'MAT{_p}',
            especialidad=self.especialidad
        )
    
    def test_creacion_hibrida_con_medico_externo(self):
        """
        Test Creación Híbrida: Crea solicitud con medico_externo_nombre.
        Verifica que se creen los ResultadoExamen vacíos automáticamente.
        """
        data = {
            'paciente_id': self.paciente.id,
            'medico_externo_nombre': 'Dr. Externo',
            'origen_solicitud': 'EXTERNO_CEHTA',
            'examenes_ids': [self.tipo_examen_1.id],
        }
        
        response = self.client.post('/api/lab/solicitudes/', data, format='json')
        
        # Verificar que se creó correctamente
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se creó la solicitud
        solicitud_id = response.data['id']
        solicitud = SolicitudExamen.objects.get(id=solicitud_id)
        
        assert solicitud.medico_externo_nombre == 'Dr. Externo'
        assert solicitud.medico_interno is None
        assert solicitud.origen_solicitud == 'EXTERNO_CEHTA'
        
        # Verificar que se crearon los ResultadoExamen vacíos automáticamente
        assert solicitud.resultados.count() == 1
        resultado = solicitud.resultados.first()
        assert resultado.tipo_examen == self.tipo_examen_1
        assert resultado.valor_obtenido == ''
        assert resultado.es_patologico is False

    def test_creacion_externo_requiere_medico(self):
        data = {
            'paciente_id': self.paciente.id,
            'origen_solicitud': 'EXTERNO_ICPL',
            'examenes_ids': [self.tipo_examen_1.id],
        }
        response = self.client.post('/api/lab/solicitudes/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'medico_externo_nombre' in response.data

    def test_creacion_externo_icpl(self):
        data = {
            'paciente_id': self.paciente.id,
            'medico_externo_nombre': 'Dra. López',
            'origen_solicitud': 'EXTERNO_ICPL',
            'examenes_ids': [self.tipo_examen_1.id],
        }
        response = self.client.post('/api/lab/solicitudes/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        solicitud = SolicitudExamen.objects.get(id=response.data['id'])
        assert solicitud.origen_solicitud == 'EXTERNO_ICPL'
        assert solicitud.medico_externo_nombre == 'Dra. López'
    
    def test_creacion_con_paneles(self):
        """
        Test que al crear una solicitud con paneles, se crean los ResultadoExamen
        para todos los exámenes del panel (evitando duplicados).
        """
        data = {
            'paciente_id': self.paciente.id,
            'medico_id': self.medico.id,
            'origen_solicitud': 'AMBULATORIO_CEHTA',
            'paneles_ids': [self.panel.id],
        }
        
        response = self.client.post('/api/lab/solicitudes/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        solicitud_id = response.data['id']
        solicitud = SolicitudExamen.objects.get(id=solicitud_id)
        
        # Verificar que se creó un resultado para el examen del panel
        assert solicitud.resultados.count() == 1
        resultado = solicitud.resultados.first()
        assert resultado.tipo_examen == self.tipo_examen_2
    
    def test_creacion_con_examenes_y_paneles_sin_duplicados(self):
        """
        Test que al crear una solicitud con exámenes y paneles que comparten exámenes,
        no se crean duplicados.
        """
        # Agregar tipo_examen_2 también al panel (ya está, pero para claridad)
        # Crear solicitud con tipo_examen_2 directo y también con el panel que lo contiene
        data = {
            'paciente_id': self.paciente.id,
            'medico_id': self.medico.id,
            'origen_solicitud': 'AMBULATORIO_CEHTA',
            'examenes_ids': [self.tipo_examen_2.id],  # Mismo examen que está en el panel
            'paneles_ids': [self.panel.id],
        }
        
        response = self.client.post('/api/lab/solicitudes/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        solicitud_id = response.data['id']
        solicitud = SolicitudExamen.objects.get(id=solicitud_id)
        
        # Debe haber solo 1 resultado (sin duplicados)
        assert solicitud.resultados.count() == 1
    
    def test_cargar_resultados(self):
        """
        Test Carga Resultados:
        - Crea solicitud
        - Llama al endpoint cargar_resultados con valores
        - Verifica que los valores se guarden en DB
        """
        # Crear solicitud
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA'
        )
        solicitud.tipos_examen.add(self.tipo_examen_1)
        
        # Crear resultado vacío
        resultado = ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=self.tipo_examen_1,
            valor_obtenido='',
            es_patologico=False
        )
        
        # Cargar resultados
        data = {
            'resultados': [
                {
                    'id': resultado.id,
                    'valor': '95.5',
                    'es_patologico': False,
                    'observaciones': 'Valor normal'
                }
            ]
        }
        
        response = self.client.post(
            f'/api/lab/solicitudes/{solicitud.id}/cargar-resultados/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar que se guardaron los valores
        resultado.refresh_from_db()
        assert resultado.valor_obtenido == '95.5'
        assert resultado.es_patologico is False
        assert resultado.observaciones == 'Valor normal'
        
        # Verificar que el estado cambió a EN_PROCESO
        solicitud.refresh_from_db()
        assert solicitud.estado == 'EN_PROCESO'
    
    def test_validacion_bloqueo(self):
        """
        Test Validación Bloqueo:
        - Valida una solicitud
        - Intenta cargar resultados de nuevo
        - Expected: 400 Bad Request o 403 Forbidden
        """
        # Crear solicitud con resultado
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='EN_PROCESO'
        )
        solicitud.tipos_examen.add(self.tipo_examen_1)
        
        resultado = ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=self.tipo_examen_1,
            valor_obtenido='95.5',
            es_patologico=False
        )
        
        # Validar la solicitud (solo rol admin en este hardening)
        self.client.force_authenticate(user=self.user_admin)
        response_validar = self.client.post(
            f'/api/lab/solicitudes/{solicitud.id}/validar/'
        )
        self.client.force_authenticate(user=self.user_lab)
        
        assert response_validar.status_code == status.HTTP_200_OK
        
        # Intentar cargar resultados de nuevo
        data = {
            'resultados': [
                {
                    'id': resultado.id,
                    'valor': '100.0',
                    'es_patologico': False,
                }
            ]
        }
        
        response_cargar = self.client.post(
            f'/api/lab/solicitudes/{solicitud.id}/cargar-resultados/',
            data,
            format='json'
        )
        
        # Debe recibir 400 Bad Request
        assert response_cargar.status_code == status.HTTP_400_BAD_REQUEST
        assert 'validada' in response_cargar.data.get('error', '').lower()
    
    def test_validar_solicitud_sin_resultados_vacios(self):
        """
        Test que no se puede validar una solicitud con resultados vacíos.
        """
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='EN_PROCESO'
        )
        solicitud.tipos_examen.add(self.tipo_examen_1)
        
        # Crear resultado vacío
        ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=self.tipo_examen_1,
            valor_obtenido='',  # Vacío
            es_patologico=False
        )
        
        # Intentar validar (solo admin)
        self.client.force_authenticate(user=self.user_admin)
        response = self.client.post(
            f'/api/lab/solicitudes/{solicitud.id}/validar/'
        )
        self.client.force_authenticate(user=self.user_lab)
        
        # Debe recibir 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'vacíos' in response.data.get('error', '').lower()
    
    def test_etiqueta_zpl(self):
        """
        Test que el endpoint etiqueta retorna datos ZPL.
        """
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA'
        )
        
        response = self.client.get(
            f'/api/lab/solicitudes/{solicitud.id}/etiqueta/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'zpl' in response.data
        assert 'protocolo' in response.data
        assert response.data['protocolo'] == solicitud.numero
        assert response.data['paciente'] == solicitud.paciente.nombre_completo
    
    def test_filtro_por_numero(self):
        """
        Test que el filtro por número funciona para código de barras.
        """
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA'
        )
        
        # Buscar por número
        response = self.client.get(
            f'/api/lab/solicitudes/?numero={solicitud.numero}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['numero'] == solicitud.numero


@pytest.mark.django_db
class TestLimsAuthorization(APITestCase):
    """Comprobaciones mínimas de permisos LIMS (hardening provisional)."""

    def setUp(self):
        _p = 'LAUTH'
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f'SNG{_p}',
            nombre='Sangre',
            color_tubo='Rojo',
            activo=True,
        )
        self.tipo_examen = TipoExamen.objects.create(
            codigo=f'GLU{_p}',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=100.00,
            rango_referencia_texto='70-100 mg/dL',
            activo=True,
        )
        self.especialidad = Especialidad.objects.create(nombre=f'Cardiología {_p}')
        self.medico = Medico.objects.create(
            nombre='Dr. Solo',
            apellido='Propio',
            matricula=f'MAT{_p}',
            especialidad=self.especialidad,
        )
        self.paciente = Paciente.objects.create(
            dni='88888888',
            nombre='Ana',
            apellido='Paciente',
        )
        self.user_medico = User.objects.create_user(
            username='medico_lims',
            email='medico-lims@test.com',
            password='medpass123',
            rol='medico',
        )
        self.medico.user = self.user_medico
        self.medico.save()
        self.user_lab = User.objects.create_user(
            username='lab_auth',
            email='lab-auth@test.com',
            password='labpass123',
            rol='laboratorio',
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username='admin_auth',
            email='admin-auth@test.com',
            password='admpass123',
            rol='admin',
            is_staff=True,
        )
        self.sol_medico = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA',
        )
        self.sol_medico.tipos_examen.add(self.tipo_examen)

    def test_anonimo_denegado_solicitudes_y_catalogo(self):
        self.client.logout()
        r_list = self.client.get('/api/lab/solicitudes/')
        assert r_list.status_code == status.HTTP_403_FORBIDDEN
        r_cat = self.client.get('/api/lab/muestras/')
        assert r_cat.status_code == status.HTTP_403_FORBIDDEN

    def test_medico_lista_solo_sus_solicitudes(self):
        otro = Medico.objects.create(
            nombre='Otro',
            apellido='Médico',
            matricula='MAT-OT-LAUTH',
            especialidad=self.especialidad,
        )
        SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=otro,
            origen_solicitud='AMBULATORIO_CEHTA',
        )
        self.client.force_authenticate(user=self.user_medico)
        r = self.client.get('/api/lab/solicitudes/')
        assert r.status_code == status.HTTP_200_OK
        assert len(r.data['results']) == 1
        assert r.data['results'][0]['id'] == self.sol_medico.id

    def test_medico_no_puede_cargar_resultados(self):
        res = ResultadoExamen.objects.create(
            solicitud=self.sol_medico,
            tipo_examen=self.tipo_examen,
            valor_obtenido='',
            es_patologico=False,
        )
        self.client.force_authenticate(user=self.user_medico)
        r = self.client.post(
            f'/api/lab/solicitudes/{self.sol_medico.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '1'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_validar(self):
        ResultadoExamen.objects.create(
            solicitud=self.sol_medico,
            tipo_examen=self.tipo_examen,
            valor_obtenido='10',
            es_patologico=False,
        )
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f'/api/lab/solicitudes/{self.sol_medico.id}/validar/',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_puede_cargar_resultados(self):
        res = ResultadoExamen.objects.create(
            solicitud=self.sol_medico,
            tipo_examen=self.tipo_examen,
            valor_obtenido='',
            es_patologico=False,
        )
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f'/api/lab/solicitudes/{self.sol_medico.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '5.5'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_admin_puede_validar(self):
        ResultadoExamen.objects.create(
            solicitud=self.sol_medico,
            tipo_examen=self.tipo_examen,
            valor_obtenido='10',
            es_patologico=False,
        )
        self.sol_medico.estado = 'EN_PROCESO'
        self.sol_medico.save(update_fields=['estado'])
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(
            f'/api/lab/solicitudes/{self.sol_medico.id}/validar/',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_secretaria_y_enfermeria_listan_solo_pendiente_y_finalizado(self):
        sec = User.objects.create_user(
            username='sec_lims',
            email='sec@test.com',
            password='x',
            rol='secretaria',
        )
        enf = User.objects.create_user(
            username='enf_lims',
            email='enf@test.com',
            password='x',
            rol='enfermeria',
        )
        self.sol_medico.estado = 'EN_PROCESO'
        self.sol_medico.save(update_fields=['estado'])

        self.client.force_authenticate(user=sec)
        r = self.client.get('/api/lab/solicitudes/')
        assert r.status_code == status.HTTP_200_OK
        estados = {item['estado'] for item in r.data}
        assert estados.issubset({'PENDIENTE', 'FINALIZADO'})

        self.client.force_authenticate(user=enf)
        r2 = self.client.get('/api/lab/solicitudes/')
        assert r2.status_code == status.HTTP_200_OK
        estados2 = {item['estado'] for item in r2.data}
        assert estados2.issubset({'PENDIENTE', 'FINALIZADO'})

    def test_secretaria_y_enfermeria_no_leen_catalogo_lims(self):
        sec = User.objects.create_user(
            username='sec_cat',
            email='sec-cat@test.com',
            password='x',
            rol='secretaria',
        )
        enf = User.objects.create_user(
            username='enf_cat',
            email='enf-cat@test.com',
            password='x',
            rol='enfermeria',
        )
        self.client.force_authenticate(user=sec)
        assert self.client.get('/api/lab/muestras/').status_code == status.HTTP_403_FORBIDDEN
        self.client.force_authenticate(user=enf)
        assert self.client.get('/api/lab/examenes/').status_code == status.HTTP_403_FORBIDDEN

    def test_alias_laboratorio_misma_proteccion(self):
        self.client.force_authenticate(user=self.user_lab)
        assert self.client.get('/api/laboratorio/tipos-examen/').status_code == status.HTTP_200_OK
        self.client.logout()
        assert self.client.get('/api/laboratorio/solicitudes/').status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_lista_sus_ordenes_lims(self):
        pac_user = User.objects.create_user(
            username='pac_lims',
            email='pac@test.com',
            password='x',
            rol='paciente',
        )
        paciente = Paciente.objects.create(
            user=pac_user,
            nombre='Ana',
            apellido='Test',
            dni='99111222',
            fecha_nacimiento='1990-01-01',
        )
        SolicitudExamen.objects.create(
            paciente=paciente,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='PENDIENTE',
        )
        self.client.force_authenticate(user=pac_user)
        r = self.client.get('/api/lab/solicitudes/')
        assert r.status_code == status.HTTP_200_OK
        assert r.data['count'] >= 1
        assert self.client.get('/api/lab/muestras/').status_code == status.HTTP_403_FORBIDDEN


class TestLimsAuditTrail(APITestCase):
    """Auditoría append-only en validación y borrado de órdenes LIMS.

    Los inserts en ``AuditEvent`` van por ``transaction.on_commit``; en ``TestCase``
    la transacción del test no hace commit real. Use ``captureOnCommitCallbacks``
    (API en ``django.test.TransactionTestCase`` / ``TestCase``).
    """

    def setUp(self):
        _p = 'LAUD'
        self.user_admin = User.objects.create_user(
            username='audit_admin',
            email='audit-admin@test.com',
            password='admpass123',
            rol='admin',
            is_staff=True,
        )
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f'SNG{_p}',
            nombre='Sangre',
            color_tubo='Rojo',
            activo=True,
        )
        self.tipo_examen = TipoExamen.objects.create(
            codigo=f'GLU{_p}',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=100.00,
            rango_referencia_texto='70-100 mg/dL',
            activo=True,
        )
        self.especialidad = Especialidad.objects.create(nombre=f'Cardiología {_p}')
        self.medico = Medico.objects.create(
            nombre='Dr. Audit',
            apellido='Médico',
            matricula=f'MAT{_p}',
            especialidad=self.especialidad,
        )
        self.paciente = Paciente.objects.create(
            dni='77777777',
            nombre='Pedro',
            apellido='Audit',
        )

    def test_validar_deja_audit_event_resultado_con_before_state(self):
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA',
            estado='EN_PROCESO',
        )
        solicitud.tipos_examen.add(self.tipo_examen)
        resultado = ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=self.tipo_examen,
            valor_obtenido='12',
            es_patologico=False,
        )
        self.client.force_authenticate(user=self.user_admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f'/api/lab/solicitudes/{solicitud.id}/validar/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ev = (
            AuditEvent.objects.filter(
                entity_type=ResultadoExamen._meta.label,
                entity_id=str(resultado.id),
                action='UPDATE',
                module='laboratorio',
            )
            .order_by('-timestamp', '-id')
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertIsNotNone(ev.before_state)
        self.assertIsNotNone(ev.after_state)

    def test_destroy_deja_audit_event_delete_con_before_state(self):
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA',
        )
        solicitud.tipos_examen.add(self.tipo_examen)
        sid = solicitud.id
        self.client.force_authenticate(user=self.user_admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(f'/api/lab/solicitudes/{sid}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        ev = AuditEvent.objects.filter(
            entity_type=SolicitudExamen._meta.label,
            entity_id=str(sid),
            action='DELETE',
            module='laboratorio',
        ).first()
        self.assertIsNotNone(ev)
        self.assertIsNotNone(ev.before_state)

    def test_destroy_entity_repr_sin_nombre_paciente(self):
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud='AMBULATORIO_CEHTA',
        )
        solicitud.tipos_examen.add(self.tipo_examen)
        sid = solicitud.id
        self.client.force_authenticate(user=self.user_admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(f'/api/lab/solicitudes/{sid}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        ev = AuditEvent.objects.filter(
            entity_type=SolicitudExamen._meta.label,
            entity_id=str(sid),
            action='DELETE',
            module='laboratorio',
        ).first()
        self.assertIsNotNone(ev)
        self.assertTrue(ev.entity_repr.startswith('laboratorio.SolicitudExamen:'))
        self.assertNotIn('Pedro', ev.entity_repr)
        self.assertNotIn('Audit', ev.entity_repr)
        self.assertNotIn(self.paciente.dni, ev.entity_repr)


@pytest.mark.django_db
class TestSolicitudExamenEstadoAPI(APITestCase):
    """Máquina de estados mínima: transiciones, PATCH y permisos."""

    def setUp(self):
        _p = 'TFSM'
        self.user_lab = User.objects.create_user(
            username='lab_fsm',
            email='lab-fsm@test.com',
            password='testpass123',
            rol='laboratorio',
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username='admin_fsm',
            email='admin-fsm@test.com',
            password='adminpass123',
            rol='admin',
            is_staff=True,
        )
        self.user_medico = User.objects.create_user(
            username='med_fsm',
            email='med-fsm@test.com',
            password='medpass123',
            rol='medico',
        )
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f'SNG{_p}',
            nombre='Sangre',
            color_tubo='Rojo',
            activo=True,
        )
        self.tipo_examen_a = TipoExamen.objects.create(
            codigo=f'GLU{_p}',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=100.00,
            activo=True,
        )
        self.tipo_examen_b = TipoExamen.objects.create(
            codigo=f'HEM{_p}',
            nombre='Hemoglobina',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=150.00,
            activo=True,
        )
        self.especialidad = Especialidad.objects.create(nombre=f'Cardiología {_p}')
        self.medico = Medico.objects.create(
            nombre='Dr. FSM',
            apellido='Médico',
            matricula=f'MAT{_p}',
            especialidad=self.especialidad,
            user=self.user_medico,
        )
        self.paciente = Paciente.objects.create(
            dni='87654321',
            nombre='Pac',
            apellido='iente',
        )
        self.client.force_authenticate(user=self.user_lab)

    def _crear_solicitud_api(self, examenes_ids=None):
        if examenes_ids is None:
            examenes_ids = [self.tipo_examen_a.id]
        r = self.client.post(
            '/api/lab/solicitudes/',
            {
                'paciente_id': self.paciente.id,
                'medico_id': self.medico.id,
                'origen_solicitud': 'AMBULATORIO_CEHTA',
                'examenes_ids': examenes_ids,
            },
            format='json',
        )
        assert r.status_code == status.HTTP_201_CREATED, r.data
        return SolicitudExamen.objects.get(id=r.data['id'])

    def test_flujo_completo_estados(self):
        sol = self._crear_solicitud_api(examenes_ids=[self.tipo_examen_a.id, self.tipo_examen_b.id])
        assert sol.estado == 'PENDIENTE'

        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json').status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

        ra = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        rb = sol.resultados.get(tipo_examen=self.tipo_examen_b)

        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': ra.id, 'valor': '90'}]},
            format='json',
        ).status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': rb.id, 'valor': '12'}]},
            format='json',
        ).status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

        # Técnico no puede validar
        r_lab_validar = self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json')
        assert r_lab_validar.status_code == status.HTTP_403_FORBIDDEN

        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/validar/',
            {},
            format='json',
        ).status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'FINALIZADO'

        # Tras validar, bloqueado
        self.client.force_authenticate(user=self.user_lab)
        r_bloqueado = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': ra.id, 'valor': '95'}]},
            format='json',
        )
        assert r_bloqueado.status_code == status.HTTP_400_BAD_REQUEST
        ra.refresh_from_db()
        assert ra.valor_obtenido == '90'

    def test_cargar_desde_pendiente_requiere_toma_muestra(self):
        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '88'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        sol.refresh_from_db()
        assert sol.estado == 'PENDIENTE'

    def test_tomar_muestra_dos_veces_400(self):
        sol = self._crear_solicitud_api()
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json').status_code == 200
        r = self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_tomar_muestra_con_payload_crea_tubos_pendientes_extraccion(self):
        sol = self._crear_solicitud_api()
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/tomar-muestra/',
            {'muestras': [{'tipo_muestra_id': self.tipo_muestra.id}]},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK, r.data
        sol.refresh_from_db()
        # Imprimir etiquetas no toma ni avanza la orden.
        assert sol.estado == 'PENDIENTE'
        muestras = Muestra.objects.filter(solicitud=sol)
        assert muestras.count() == 1
        m = muestras.get()
        assert m.estado == 'PENDIENTE_TOMA'
        assert m.tipo_muestra_id == self.tipo_muestra.id
        assert r.data.get('extraccion_completa') is False
        assert len(r.data.get('tubos_pendientes_extraccion') or []) == 1

        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                '/api/lab/muestras-transaccionales/recibir-por-codigo/',
                {'codigo_barra': m.codigo_barra, 'ubicacion_actual': 'Lab'},
                format='json',
            )
        assert r2.status_code == status.HTTP_200_OK, r2.data
        assert r2.data['estado'] == 'RECIBIDA'
        assert r2.data.get('extraccion_completa') is True
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

    def test_tomar_muestra_varios_tipos_en_un_paso(self):
        tm_orina = TipoMuestra.objects.create(
            codigo='ORI_TMS',
            nombre='Orina',
            color_tubo='Amarillo',
            activo=True,
        )
        te_orina = TipoExamen.objects.create(
            codigo='URO_TMS',
            nombre='Urocultivo',
            tipo_muestra_requerida=tm_orina,
            precio=200.00,
            activo=True,
        )
        sol = self._crear_solicitud_api(examenes_ids=[self.tipo_examen_a.id, te_orina.id])
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/tomar-muestra/',
            {
                'muestras': [
                    {'tipo_muestra_id': self.tipo_muestra.id},
                    {'tipo_muestra_id': tm_orina.id},
                ]
            },
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK, r.data
        sol.refresh_from_db()
        assert sol.estado == 'PENDIENTE'
        assert Muestra.objects.filter(solicitud=sol, estado='PENDIENTE_TOMA').count() == 2

        for m in Muestra.objects.filter(solicitud=sol):
            with self.captureOnCommitCallbacks(execute=True):
                rt = self.client.post(
                    '/api/lab/muestras-transaccionales/recibir-por-codigo/',
                    {'codigo_barra': m.codigo_barra},
                    format='json',
                )
            assert rt.status_code == status.HTTP_200_OK, rt.data
            assert rt.data['estado'] == 'RECIBIDA'

        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'
        assert Muestra.objects.filter(solicitud=sol, estado='RECIBIDA').count() == 2

    def test_tomar_muestra_tipo_inactivo_400(self):
        tm_extra = TipoMuestra.objects.create(
            codigo='EXT_TMS',
            nombre='Extra',
            color_tubo='Verde',
            activo=False,
        )
        sol = self._crear_solicitud_api()
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/tomar-muestra/',
            {'muestras': [{'tipo_muestra_id': tm_extra.id}]},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_crear_tipo_muestra_api(self):
        r = self.client.post(
            '/api/lab/muestras/',
            {'codigo': 'LCR_TMS', 'nombre': 'LCR', 'color_tubo': 'Transparente', 'activo': True},
            format='json',
        )
        assert r.status_code == status.HTTP_201_CREATED, r.data
        assert r.data['codigo'] == 'LCR_TMS'
        assert TipoMuestra.objects.filter(codigo='LCR_TMS').exists()

    def test_fecha_muestra_excluye_pendientes(self):
        sol_p = self._crear_solicitud_api()
        assert sol_p.estado == 'PENDIENTE'
        hoy = timezone.now().date().isoformat()
        r_pend = self.client.get('/api/lab/solicitudes/', {'fecha_muestra': hoy}, format='json')
        assert r_pend.status_code == 200
        ids_pend = {x['id'] for x in r_pend.data.get('results', r_pend.data)}
        assert sol_p.id not in ids_pend

        sol_t = self._crear_solicitud_api()
        assert self.client.post(
            f'/api/lab/solicitudes/{sol_t.id}/tomar-muestra/',
            {'muestras': [{'tipo_muestra_id': self.tipo_muestra.id}]},
            format='json',
        ).status_code == 200
        r_toma = self.client.get('/api/lab/solicitudes/', {'fecha_muestra': hoy}, format='json')
        ids_toma = {x['id'] for x in r_toma.data.get('results', r_toma.data)}
        assert sol_t.id in ids_toma

        r_estado = self.client.get('/api/lab/solicitudes/', {'estado': 'PENDIENTE'}, format='json')
        ids_est = {x['id'] for x in r_estado.data.get('results', r_estado.data)}
        assert sol_p.id in ids_est
        assert sol_t.id not in ids_est

    def test_acciones_cancelar_y_entregado_eliminadas(self):
        sol = self._crear_solicitud_api()
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/cancelar/', {}, format='json').status_code == 404
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/marcar-entregado/', {}, format='json').status_code == 404

    def test_cargar_finalizado_bloqueado(self):
        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')
        self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '1'}]},
            format='json',
        )
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'
        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json').status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'FINALIZADO'
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '2'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        res.refresh_from_db()
        assert res.valor_obtenido == '1'

    def test_finalizar_sin_en_proceso(self):
        sol_p = self._crear_solicitud_api()
        rp = sol_p.resultados.get(tipo_examen=self.tipo_examen_a)
        rp.valor_obtenido = '8'
        rp.save()
        self.client.force_authenticate(user=self.user_admin)
        r_pend = self.client.post(f'/api/lab/solicitudes/{sol_p.id}/finalizar/', {}, format='json')
        assert r_pend.status_code == status.HTTP_400_BAD_REQUEST

        sol_ok = self._crear_solicitud_api()
        r_ok = sol_ok.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.force_authenticate(user=self.user_lab)
        self.client.post(f'/api/lab/solicitudes/{sol_ok.id}/tomar-muestra/', {}, format='json')
        self.client.post(
            f'/api/lab/solicitudes/{sol_ok.id}/cargar-resultados/',
            {'resultados': [{'id': r_ok.id, 'valor': '9'}]},
            format='json',
        )
        sol_ok.refresh_from_db()
        assert sol_ok.estado == 'EN_PROCESO'
        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(f'/api/lab/solicitudes/{sol_ok.id}/validar/', {}, format='json').status_code == 200
        sol_ok.refresh_from_db()
        assert sol_ok.estado == 'FINALIZADO'
        assert self.client.post(f'/api/lab/solicitudes/{sol_ok.id}/finalizar/', {}, format='json').status_code == 400

    def test_patch_no_cambia_estado(self):
        sol = self._crear_solicitud_api()
        r = self.client.patch(
            f'/api/lab/solicitudes/{sol.id}/',
            {'estado': 'FINALIZADO', 'observaciones': 'nota fsm'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'PENDIENTE'
        assert sol.observaciones == 'nota fsm'

    def test_no_auto_finalizar_al_cargar_resultados(self):
        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '5'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

    def test_finalizar_con_muestra_tomada_vinculada(self):
        """Al validar, recepciona muestras TOMADA antes de finalizar."""
        from laboratorio.muestra_estado import aplicar_tomar, crear_muestra

        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')
        muestra = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.id,
            tipo_contenedor_id=None,
            observaciones='',
            actor=self.user_lab,
            view='test',
        )
        aplicar_tomar(muestra.pk, actor=self.user_lab, view='test')
        muestra.refresh_from_db()
        assert muestra.estado == 'TOMADA'
        res.muestra = muestra
        res.save(update_fields=['muestra'])
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '7.2'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK, r.data
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'
        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json').status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'FINALIZADO'
        muestra.refresh_from_db()
        assert muestra.estado in ('RECIBIDA', 'EN_PROCESO', 'CONSERVADA')

    def test_carga_parcial_informar_parcial_estado(self):
        sol = self._crear_solicitud_api(examenes_ids=[self.tipo_examen_a.id, self.tipo_examen_b.id])
        ra = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        rb = sol.resultados.get(tipo_examen=self.tipo_examen_b)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')

        r_avance = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': ra.id, 'valor': '90'}]},
            format='json',
        )
        assert r_avance.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'
        rb.refresh_from_db()
        assert rb.valor_obtenido == ''

        r_parcial = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {
                'informar_parcial': True,
                'resultados': [{'id': ra.id, 'valor': '91'}],
            },
            format='json',
        )
        assert r_parcial.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'INFORMADO_PARCIAL'
        ra.refresh_from_db()
        assert ra.valor_obtenido == '91'

        r_completo = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': rb.id, 'valor': '12'}]},
            format='json',
        )
        assert r_completo.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'INFORMADO_PARCIAL'
        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json').status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'FINALIZADO'

    def test_carga_sin_valores_rechazada(self):
        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': ''}]},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_medico_no_puede_tomar_muestra_ni_finalizar(self):
        sol = self._crear_solicitud_api()
        self.client.force_authenticate(user=self.user_medico)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json').status_code == 403
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/finalizar/', {}, format='json').status_code == 403


@pytest.mark.django_db
class TestSolicitudExamenEstadoAuditoria(APITestCase):
    def setUp(self):
        _p = 'TFSA'
        self.user_lab = User.objects.create_user(
            username='lab_audit_fsm',
            email='lab-audit@test.com',
            password='x',
            rol='laboratorio',
            is_staff=True,
        )
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f'SNG{_p}',
            nombre='Sangre',
            color_tubo='Rojo',
            activo=True,
        )
        self.tipo_examen = TipoExamen.objects.create(
            codigo=f'GLU{_p}',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tipo_muestra,
            precio=1,
            activo=True,
        )
        self.especialidad = Especialidad.objects.create(nombre=f'ESP {_p}')
        self.medico = Medico.objects.create(
            nombre='Dr',
            apellido='A',
            matricula=f'M{_p}',
            especialidad=self.especialidad,
        )
        self.paciente = Paciente.objects.create(dni='11112222', nombre='A', apellido='B')

    def test_validar_audit_event_metadata(self):
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            '/api/lab/solicitudes/',
            {
                'paciente_id': self.paciente.id,
                'medico_id': self.medico.id,
                'origen_solicitud': 'AMBULATORIO_CEHTA',
                'examenes_ids': [self.tipo_examen.id],
            },
            format='json',
        )
        sid = r.data['id']
        res = ResultadoExamen.objects.get(solicitud_id=sid)
        self.client.post(f'/api/lab/solicitudes/{sid}/tomar-muestra/', {}, format='json')
        self.client.post(
            f'/api/lab/solicitudes/{sid}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '7'}]},
            format='json',
        )
        sol = SolicitudExamen.objects.get(pk=sid)
        self.assertEqual(sol.estado, 'EN_PROCESO')

        user_bio = User.objects.create_user(
            username='bio_audit_fsm',
            email='bio-audit@test.com',
            password='x',
            rol='bioquimico',
            is_staff=True,
        )
        self.client.force_authenticate(user=user_bio)
        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f'/api/lab/solicitudes/{sid}/validar/',
                {},
                format='json',
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, 'FINALIZADO')

        ev = (
            AuditEvent.objects.filter(
                entity_type=SolicitudExamen._meta.label,
                entity_id=str(sid),
                action='UPDATE',
                module='laboratorio',
                metadata__accion='validar',
            )
            .order_by('-timestamp', '-id')
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertIsNotNone(ev.metadata)
        self.assertEqual(ev.metadata.get('accion'), 'validar')
        self.assertEqual(ev.metadata.get('estado_anterior'), 'EN_PROCESO')
        self.assertEqual(ev.metadata.get('estado_nuevo'), 'FINALIZADO')


