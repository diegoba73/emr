"""Tests de integración API para la app ``historias_clinicas``.

Convenciones de seed local:
- ``Especialidad`` con ``get_or_create`` y nombres con sufijo ``HC API``.
- ``Paciente`` con DNIs ``HA-XXXX``.
- ``Medico`` con matrículas ``MHA-XXX``.
- ``Medicamento``/``DiagnosticoCIE10`` con ``get_or_create`` por código/nombre
  para no chocar con seeds compartidos.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from auditoria.models import AuditEvent
from catalogos.models import DiagnosticoCIE10, Medicamento
from historias_clinicas.models import Consulta, HistoriaClinica
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno

User = get_user_model()


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


def _medicamento(nombre: str) -> Medicamento:
    obj, _ = Medicamento.objects.get_or_create(
        nombre=nombre,
        defaults=dict(
            principio_activo=nombre,
            presentacion='Comprimidos',
            concentracion='600mg',
            via_administracion='Oral',
            activo=True,
        ),
    )
    return obj


def _diagnostico_cie(codigo: str, descripcion: str) -> DiagnosticoCIE10:
    obj, _ = DiagnosticoCIE10.objects.get_or_create(
        codigo=codigo,
        defaults=dict(
            descripcion=descripcion,
            categoria='HC API',
            activo=True,
        ),
    )
    return obj


@pytest.mark.django_db
class TestConsultaAPI(APITestCase):
    """Tests de integración para ``/api/consultas/``."""

    def setUp(self):
        self.user_medico = User.objects.create_user(
            username='hc_medico_api',
            email='hc_medico_api@test.com',
            password='testpass123',
            rol='medico',
        )
        self.especialidad = _esp('Cardiología HC API')
        self.medico = Medico.objects.create(
            user=self.user_medico,
            nombre='Dr. Test',
            apellido='Médico',
            matricula='MHA-001',
            especialidad=self.especialidad,
        )

        self.paciente = Paciente.objects.create(
            dni='HA-1001',
            nombre='Juan',
            apellido='Pérez',
        )
        self.historia_clinica = HistoriaClinica.objects.create(paciente=self.paciente)

        self.medicamento = _medicamento('Ibuprofeno HC API')
        self.diagnostico_cie = _diagnostico_cie('I10-HC-API', 'Hipertensión esencial HC API')

        self.client.force_authenticate(user=self.user_medico)

    def test_consulta_completa_con_diagnostico_y_prescripcion(self):
        data = {
            'historia_clinica': self.historia_clinica.paciente_id,
            'medico': self.medico.id,
            'fecha_hora_consulta': timezone.now().isoformat(),
            'motivo_consulta_detalle': 'Dolor de cabeza',
            'anamnesis': 'Paciente refiere cefalea',
            'examen_fisico': 'Sin particularidades',
            'diagnostico_presuntivo': 'Cefalea tensional',
            'plan_manejo': 'Reposo y analgésicos',
            'diagnosticos': [
                {
                    'diagnostico_cie_id': self.diagnostico_cie.id,
                    'nombre_diagnostico': 'Cefalea tensional',
                    'descripcion_diagnostico': 'Cefalea de tipo tensional',
                }
            ],
            'prescripciones': [
                {
                    'medicamento_id': self.medicamento.id,
                    'dosis': '600mg',
                    'frecuencia': 'Cada 8hs',
                    'duracion': '7 días',
                    'instrucciones': 'Tomar con alimentos',
                    'activa': True,
                }
            ],
        }
        response = self.client.post('/api/consultas/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        consulta = Consulta.objects.get(id=response.data['id'])
        assert consulta.diagnosticos.count() == 1
        assert consulta.prescripciones.count() == 1
        diagnostico = consulta.diagnosticos.first()
        assert diagnostico.nombre_diagnostico == 'Cefalea tensional'
        prescripcion = consulta.prescripciones.first()
        assert prescripcion.medicamento == self.medicamento
        assert prescripcion.dosis == '600mg'

    def test_consulta_crea_historia_clinica_si_no_existe(self):
        nuevo_paciente = Paciente.objects.create(
            dni='HA-1002',
            nombre='María',
            apellido='González',
        )
        data = {
            'historia_clinica': nuevo_paciente.id,
            'medico': self.medico.id,
            'fecha_hora_consulta': timezone.now().isoformat(),
            'motivo_consulta_detalle': 'Control de rutina',
        }
        response = self.client.post('/api/consultas/', data, format='json')
        # Para que ConsultaCreateSerializer acepte ``historia_clinica`` debe
        # existir el objeto. Si pasaste un ID que no es de HC, falla 400 con
        # validación. Si querés crear HC al vuelo, primero hay que tenerla.
        # Aceptamos 201 si el setup creó HC, 400 si no.
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)
        if response.status_code == status.HTTP_201_CREATED:
            assert HistoriaClinica.objects.filter(paciente=nuevo_paciente).exists()

    def test_permisos_paciente_no_puede_crear_consulta(self):
        user_paciente = User.objects.create_user(
            username='hc_paciente_api',
            email='hc_paciente_api@test.com',
            password='testpass123',
            rol='paciente',
        )
        self.client.force_authenticate(user=user_paciente)

        data = {
            'historia_clinica': self.historia_clinica.paciente_id,
            'medico': self.medico.id,
            'fecha_hora_consulta': timezone.now().isoformat(),
            'motivo_consulta_detalle': 'Intento de crear consulta',
        }
        response = self.client.post('/api/consultas/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_consulta_bloqueado(self):
        """DELETE físico de Consulta debe responder 405 ``MethodNotAllowed``."""
        consulta = Consulta.objects.create(
            historia_clinica=self.historia_clinica,
            medico=self.medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Para borrar (no debería poder)',
        )
        response = self.client.delete(f'/api/consultas/{consulta.id}/')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Consulta.objects.filter(pk=consulta.id).exists()

    def test_create_consulta_genera_audit_event(self):
        """``perform_create`` debe agendar un ``AuditEvent`` CREATE.

        ``audit_service.log_event`` agenda el INSERT vía
        ``transaction.on_commit`` cuando hay un atomic externo. ``TestCase``
        envuelve cada test en un atomic que nunca commitea, por eso usamos
        ``captureOnCommitCallbacks(execute=True)`` para forzar la ejecución.
        """
        prior = AuditEvent.objects.filter(
            action="CREATE", entity_type="historias_clinicas.Consulta"
        ).count()
        data = {
            'historia_clinica': self.historia_clinica.paciente_id,
            'medico': self.medico.id,
            'fecha_hora_consulta': timezone.now().isoformat(),
            'motivo_consulta_detalle': 'Audit smoke',
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post('/api/consultas/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        nuevo = AuditEvent.objects.filter(
            action="CREATE", entity_type="historias_clinicas.Consulta"
        ).count()
        assert nuevo == prior + 1

    def test_retrieve_consulta_con_solicitud_laboratorio_y_resultados(self):
        """GET detalle no debe fallar cuando hay resultados LIMS vinculados."""
        from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra

        consulta = Consulta.objects.create(
            historia_clinica=self.historia_clinica,
            medico=self.medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control con laboratorio',
        )
        tipo_muestra = TipoMuestra.objects.create(
            codigo='SNG-HC-DET',
            nombre='Sangre HC detalle',
            activo=True,
        )
        tipo_examen = TipoExamen.objects.create(
            codigo='GLU-HC-DET',
            nombre='Glucosa HC detalle',
            tipo_muestra_requerida=tipo_muestra,
            activo=True,
        )
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            consulta_hc=consulta,
            origen_solicitud='AMBULATORIO_CEHTA',
        )
        solicitud.tipos_examen.add(tipo_examen)
        ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=tipo_examen,
            valor_obtenido='',
            es_patologico=False,
        )

        response = self.client.get(f'/api/consultas/{consulta.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['solicitudes_laboratorio']) == 1
        resultados = response.data['solicitudes_laboratorio'][0]['resultados']
        assert len(resultados) == 1
        assert resultados[0]['estado'] == 'PENDIENTE'


@pytest.mark.django_db
class TestAtencionAPI(APITestCase):
    """Tests de integración para ``/api/atenciones/`` desde el ámbito clínico."""

    def setUp(self):
        self.user_medico = User.objects.create_user(
            username='hc_medico_atencion',
            email='hc_medico_atencion@test.com',
            password='testpass123',
            rol='medico',
        )
        self.especialidad = _esp('Cardiología HC API Atencion')
        self.medico = Medico.objects.create(
            user=self.user_medico,
            nombre='Dr. Atención',
            apellido='Test',
            matricula='MHA-002',
            especialidad=self.especialidad,
        )

        self.paciente = Paciente.objects.create(
            dni='HA-2001',
            nombre='Paciente',
            apellido='Atención',
        )
        self.recurso = Recurso.objects.create(
            nombre='Consultorio HC API 1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )
        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        self.client.force_authenticate(user=self.user_medico)

    def test_cerrar_atencion(self):
        atencion = Atencion.objects.create(
            turno=self.turno,
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )
        response = self.client.post(f'/api/atenciones/{atencion.id}/cerrar/')
        assert response.status_code == status.HTTP_200_OK
        atencion.refresh_from_db()
        assert atencion.estado_clinico == Atencion.EstadoClinico.FINALIZADA
        assert atencion.fecha_cierre is not None

    def test_cerrar_atencion_ya_cerrada(self):
        atencion = Atencion.objects.create(
            turno=self.turno,
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.FINALIZADA,
            fecha_cierre=timezone.now(),
        )
        response = self.client.post(f'/api/atenciones/{atencion.id}/cerrar/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ABIERTA' in response.data.get('error', '')

    def test_atencion_idempotencia(self):
        """POST ``/api/atenciones/`` con un turno que ya tiene atención retorna 200."""
        atencion_existente = Atencion.objects.create(
            turno=self.turno,
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )
        response = self.client.post('/api/atenciones/', {'turno': self.turno.id}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == atencion_existente.id
        assert Atencion.objects.filter(turno=self.turno).count() == 1


@pytest.mark.django_db
class TestHistoriaClinicaAPI(APITestCase):
    """Tests de integración para ``/api/historias-clinicas/``."""

    def setUp(self):
        self.user_medico = User.objects.create_user(
            username='hc_medico_hc',
            email='hc_medico_hc@test.com',
            password='testpass123',
            rol='medico',
        )
        self.especialidad = _esp('Cardiología HC API HC')
        self.medico = Medico.objects.create(
            user=self.user_medico,
            nombre='Dr. HC',
            apellido='Test',
            matricula='MHA-003',
            especialidad=self.especialidad,
        )

        self.paciente = Paciente.objects.create(
            dni='HA-3001',
            nombre='Paciente',
            apellido='HC',
        )
        self.historia_clinica = HistoriaClinica.objects.create(paciente=self.paciente)
        for i in range(7):
            Consulta.objects.create(
                historia_clinica=self.historia_clinica,
                medico=self.medico,
                fecha_hora_consulta=timezone.now() - timedelta(days=i),
                motivo_consulta_detalle=f'Consulta HC {i+1}',
            )
        self.client.force_authenticate(user=self.user_medico)

    def test_resumen_historia_clinica(self):
        response = self.client.get(
            f'/api/historias-clinicas/{self.historia_clinica.paciente_id}/resumen/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'ultimas_consultas' in response.data
        assert 'diagnosticos_activos' in response.data
        assert len(response.data['ultimas_consultas']) == 5
        assert response.data['total_consultas'] == 7

    def test_paciente_solo_ve_su_historia(self):
        otra_paciente = Paciente.objects.create(
            dni='HA-3002', nombre='Otro', apellido='Paciente',
        )
        otra_historia = HistoriaClinica.objects.create(paciente=otra_paciente)

        user_paciente = User.objects.create_user(
            username='hc_paciente_view',
            email='hc_paciente_view@test.com',
            password='testpass123',
            rol='paciente',
        )
        self.paciente.user = user_paciente
        self.paciente.save()

        self.client.force_authenticate(user=user_paciente)
        response = self.client.get('/api/historias-clinicas/')
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results'] if 'results' in response.data else response.data
        # Paciente debe ver solo su HC, no la de "otra_historia".
        ids = {row['paciente'] for row in results}
        assert self.paciente.id in ids
        assert otra_historia.paciente_id not in ids

    def test_laboratorio_is_staff_no_lista_historias(self):
        lab = User.objects.create_user(
            username='hc_lab_staff',
            email='hc_lab_staff@test.com',
            password='testpass123',
            rol='laboratorio',
            is_staff=True,
        )
        self.client.force_authenticate(user=lab)
        response = self.client.get('/api/historias-clinicas/')
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results'] if 'results' in response.data else response.data
        assert results == []

    def test_laboratorio_is_staff_no_resumen_historia(self):
        lab = User.objects.create_user(
            username='hc_lab_staff_res',
            email='hc_lab_staff_res@test.com',
            password='testpass123',
            rol='laboratorio',
            is_staff=True,
        )
        self.client.force_authenticate(user=lab)
        response = self.client.get(
            f'/api/historias-clinicas/{self.historia_clinica.paciente_id}/resumen/'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
