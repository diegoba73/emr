"""
Tests de integración API para la app laboratorio (LIMS).
"""
import pytest
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from laboratorio.models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
)
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
            'origen_solicitud': 'EXTERNO_PAPEL',
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
        assert solicitud.origen_solicitud == 'EXTERNO_PAPEL'
        
        # Verificar que se crearon los ResultadoExamen vacíos automáticamente
        assert solicitud.resultados.count() == 1
        resultado = solicitud.resultados.first()
        assert resultado.tipo_examen == self.tipo_examen_1
        assert resultado.valor_obtenido == ''
        assert resultado.es_patologico is False
    
    def test_creacion_con_paneles(self):
        """
        Test que al crear una solicitud con paneles, se crean los ResultadoExamen
        para todos los exámenes del panel (evitando duplicados).
        """
        data = {
            'paciente_id': self.paciente.id,
            'medico_id': self.medico.id,
            'origen_solicitud': 'EMR',
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
            'origen_solicitud': 'EMR',
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
            origen_solicitud='EMR'
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
            origen_solicitud='EMR',
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
            origen_solicitud='EMR',
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
            origen_solicitud='EMR'
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
            origen_solicitud='EMR'
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
            origen_solicitud='EMR',
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
            origen_solicitud='EMR',
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

    def test_secretaria_no_lista_solicitudes_enfermeria_si(self):
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
        self.client.force_authenticate(user=sec)
        assert self.client.get('/api/lab/solicitudes/').status_code == status.HTTP_403_FORBIDDEN
        self.client.force_authenticate(user=enf)
        assert self.client.get('/api/lab/solicitudes/').status_code == status.HTTP_403_FORBIDDEN

    def test_secretaria_y_enfermeria_pueden_leer_catalogo(self):
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
        assert self.client.get('/api/lab/muestras/').status_code == status.HTTP_200_OK
        self.client.force_authenticate(user=enf)
        assert self.client.get('/api/lab/examenes/').status_code == status.HTTP_200_OK

    def test_alias_laboratorio_misma_proteccion(self):
        self.client.force_authenticate(user=self.user_lab)
        assert self.client.get('/api/laboratorio/tipos-examen/').status_code == status.HTTP_200_OK
        self.client.logout()
        assert self.client.get('/api/laboratorio/solicitudes/').status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_sin_acceso_lims(self):
        pac_user = User.objects.create_user(
            username='pac_lims',
            email='pac@test.com',
            password='x',
            rol='paciente',
        )
        self.client.force_authenticate(user=pac_user)
        assert self.client.get('/api/lab/solicitudes/').status_code == status.HTTP_403_FORBIDDEN
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
            origen_solicitud='EMR',
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
            origen_solicitud='EMR',
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
            origen_solicitud='EMR',
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
                'origen_solicitud': 'EMR',
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
        assert sol.estado == 'TOMA_MUESTRA'

        ra = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        rb = sol.resultados.get(tipo_examen=self.tipo_examen_b)

        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': ra.id, 'valor': '90'}]},
            format='json',
        ).status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json').status_code == 400
        self.client.force_authenticate(user=self.user_lab)

        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': rb.id, 'valor': '12'}]},
            format='json',
        ).status_code == 200

        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json').status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'VALIDADO'

        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': ra.id, 'valor': '95'}]},
            format='json',
        ).status_code == 400

        self.client.force_authenticate(user=self.user_lab)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/marcar-entregado/', {}, format='json').status_code == 200
        sol.refresh_from_db()
        assert sol.estado == 'ENTREGADO'

        self.client.force_authenticate(user=self.user_admin)
        assert self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': ra.id, 'valor': '99'}]},
            format='json',
        ).status_code == 400

    def test_cargar_desde_pendiente_sin_toma_pasa_a_en_proceso(self):
        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '88'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'EN_PROCESO'

    def test_tomar_muestra_dos_veces_400(self):
        sol = self._crear_solicitud_api()
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json').status_code == 200
        r = self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancelar_pendiente_toma_en_proceso(self):
        sol_p = self._crear_solicitud_api()
        assert self.client.post(f'/api/lab/solicitudes/{sol_p.id}/cancelar/', {}, format='json').status_code == 200
        sol_p.refresh_from_db()
        assert sol_p.estado == 'CANCELADO'

        sol_t = self._crear_solicitud_api()
        self.client.post(f'/api/lab/solicitudes/{sol_t.id}/tomar-muestra/', {}, format='json')
        assert self.client.post(f'/api/lab/solicitudes/{sol_t.id}/cancelar/', {}, format='json').status_code == 200
        sol_t.refresh_from_db()
        assert sol_t.estado == 'CANCELADO'

        sol_e = self._crear_solicitud_api()
        res = sol_e.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(
            f'/api/lab/solicitudes/{sol_e.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '7'}]},
            format='json',
        )
        assert self.client.post(f'/api/lab/solicitudes/{sol_e.id}/cancelar/', {}, format='json').status_code == 200
        sol_e.refresh_from_db()
        assert sol_e.estado == 'CANCELADO'

    def test_cargar_cancelado_validado_entregado_400(self):
        sol = self._crear_solicitud_api()
        res = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/cancelar/', {}, format='json')
        r = self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': res.id, 'valor': '1'}]},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

        sol2 = self._crear_solicitud_api()
        r2 = sol2.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(
            f'/api/lab/solicitudes/{sol2.id}/cargar-resultados/',
            {'resultados': [{'id': r2.id, 'valor': '2'}]},
            format='json',
        )
        self.client.force_authenticate(user=self.user_admin)
        self.client.post(f'/api/lab/solicitudes/{sol2.id}/validar/', {}, format='json')
        self.client.force_authenticate(user=self.user_lab)
        r_bad = self.client.post(
            f'/api/lab/solicitudes/{sol2.id}/cargar-resultados/',
            {'resultados': [{'id': r2.id, 'valor': '3'}]},
            format='json',
        )
        assert r_bad.status_code == status.HTTP_400_BAD_REQUEST

        sol3 = self._crear_solicitud_api()
        r3 = sol3.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(
            f'/api/lab/solicitudes/{sol3.id}/cargar-resultados/',
            {'resultados': [{'id': r3.id, 'valor': '4'}]},
            format='json',
        )
        self.client.force_authenticate(user=self.user_admin)
        self.client.post(f'/api/lab/solicitudes/{sol3.id}/validar/', {}, format='json')
        self.client.force_authenticate(user=self.user_lab)
        self.client.post(f'/api/lab/solicitudes/{sol3.id}/marcar-entregado/', {}, format='json')
        r_ent = self.client.post(
            f'/api/lab/solicitudes/{sol3.id}/cargar-resultados/',
            {'resultados': [{'id': r3.id, 'valor': '5'}]},
            format='json',
        )
        assert r_ent.status_code == status.HTTP_400_BAD_REQUEST

    def test_validar_sin_en_proceso_o_cancelada(self):
        sol_p = self._crear_solicitud_api()
        rp = sol_p.resultados.get(tipo_examen=self.tipo_examen_a)
        rp.valor_obtenido = '8'
        rp.save()
        self.client.force_authenticate(user=self.user_admin)
        r_pend = self.client.post(f'/api/lab/solicitudes/{sol_p.id}/validar/', {}, format='json')
        assert r_pend.status_code == status.HTTP_400_BAD_REQUEST

        sol_c = self._crear_solicitud_api()
        self.client.force_authenticate(user=self.user_lab)
        self.client.post(f'/api/lab/solicitudes/{sol_c.id}/cancelar/', {}, format='json')
        self.client.force_authenticate(user=self.user_admin)
        r_c = self.client.post(f'/api/lab/solicitudes/{sol_c.id}/validar/', {}, format='json')
        assert r_c.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancelar_validado_o_entregado_400(self):
        sol = self._crear_solicitud_api()
        r = sol.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(
            f'/api/lab/solicitudes/{sol.id}/cargar-resultados/',
            {'resultados': [{'id': r.id, 'valor': '6'}]},
            format='json',
        )
        self.client.force_authenticate(user=self.user_admin)
        self.client.post(f'/api/lab/solicitudes/{sol.id}/validar/', {}, format='json')
        self.client.force_authenticate(user=self.user_lab)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/cancelar/', {}, format='json').status_code == 400

        sol2 = self._crear_solicitud_api()
        r2 = sol2.resultados.get(tipo_examen=self.tipo_examen_a)
        self.client.post(
            f'/api/lab/solicitudes/{sol2.id}/cargar-resultados/',
            {'resultados': [{'id': r2.id, 'valor': '6'}]},
            format='json',
        )
        self.client.force_authenticate(user=self.user_admin)
        self.client.post(f'/api/lab/solicitudes/{sol2.id}/validar/', {}, format='json')
        self.client.force_authenticate(user=self.user_lab)
        self.client.post(f'/api/lab/solicitudes/{sol2.id}/marcar-entregado/', {}, format='json')
        assert self.client.post(f'/api/lab/solicitudes/{sol2.id}/cancelar/', {}, format='json').status_code == 400

    def test_marcar_entregado_sin_validar_400(self):
        sol = self._crear_solicitud_api()
        r = self.client.post(f'/api/lab/solicitudes/{sol.id}/marcar-entregado/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_no_cambia_estado(self):
        sol = self._crear_solicitud_api()
        r = self.client.patch(
            f'/api/lab/solicitudes/{sol.id}/',
            {'estado': 'VALIDADO', 'observaciones': 'nota fsm'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'PENDIENTE'
        assert sol.observaciones == 'nota fsm'

    def test_alias_laboratorio_cancelar(self):
        sol = self._crear_solicitud_api()
        r = self.client.post(f'/api/laboratorio/solicitudes/{sol.id}/cancelar/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        sol.refresh_from_db()
        assert sol.estado == 'CANCELADO'

    def test_medico_no_puede_tomar_muestra_ni_cancelar(self):
        sol = self._crear_solicitud_api()
        self.client.force_authenticate(user=self.user_medico)
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/tomar-muestra/', {}, format='json').status_code == 403
        assert self.client.post(f'/api/lab/solicitudes/{sol.id}/cancelar/', {}, format='json').status_code == 403


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

    def test_cancelar_audit_event_metadata(self):
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            '/api/lab/solicitudes/',
            {
                'paciente_id': self.paciente.id,
                'medico_id': self.medico.id,
                'origen_solicitud': 'EMR',
                'examenes_ids': [self.tipo_examen.id],
            },
            format='json',
        )
        sid = r.data['id']
        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(f'/api/lab/solicitudes/{sid}/cancelar/', {}, format='json')
        self.assertEqual(r2.status_code, status.HTTP_200_OK)

        ev = (
            AuditEvent.objects.filter(
                entity_type=SolicitudExamen._meta.label,
                entity_id=str(sid),
                action='UPDATE',
                module='laboratorio',
            )
            .order_by('-timestamp', '-id')
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertIsNotNone(ev.metadata)
        self.assertEqual(ev.metadata.get('accion'), 'cancelar')
        self.assertEqual(ev.metadata.get('estado_anterior'), 'PENDIENTE')
        self.assertEqual(ev.metadata.get('estado_nuevo'), 'CANCELADO')


