"""
Tests para el AtencionViewSet - endpoint POST /api/atenciones/

Verifica que la creación de Atención desde Turno resuelve
correctamente medico_principal desde el turno.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from turnos.models import Turno, Atencion, Recurso
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from auditoria.models import AuditEvent

User = get_user_model()


class TestAtencionViewSetCreate(APITestCase):
    """Tests para POST /api/atenciones/"""

    def setUp(self):
        """Configuración inicial para cada test."""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        
        # Crear especialidad
        self.especialidad, _ = Especialidad.objects.get_or_create(nombre="Cardiología")

        # Crear usuario y médico con datos únicos
        self.user_medico, _ = User.objects.get_or_create(
            username=f'dr_test_{unique_id}',
            defaults={
                'email': f'dr_{unique_id}@test.com',
                'password': 'testpass123',
                'first_name': 'Carlos',
                'last_name': 'García',
                'rol': 'medico'
            }
        )
        self.medico, _ = Medico.objects.get_or_create(
            matricula=f'MP{unique_id}',
            defaults={
                'user': self.user_medico,
                'nombre': 'Carlos',
                'apellido': 'García',
                'especialidad': self.especialidad
            }
        )

        # Crear paciente con datos únicos
        self.user_paciente, _ = User.objects.get_or_create(
            username=f'pac_test_{unique_id}',
            defaults={
                'email': f'paciente_{unique_id}@test.com',
                'password': 'testpass123',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'rol': 'paciente'
            }
        )
        self.paciente, _ = Paciente.objects.get_or_create(
            dni=f'DNI{unique_id}',
            defaults={
                'user': self.user_paciente,
                'nombre': 'Juan',
                'apellido': 'Pérez',
                'fecha_nacimiento': '1990-01-01'
            }
        )

        # Crear recurso
        self.recurso, _ = Recurso.objects.get_or_create(
            nombre=f'Consultorio Test {unique_id}',
            defaults={
                'ubicacion': 'Piso 1',
                'tipo_recurso': Recurso.TipoRecurso.CONSULTORIO,
                'activo': True
            }
        )

        # Crear turno con médico
        self.turno_con_medico = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=timezone.now() + timedelta(hours=1),
            fecha_hora_fin=timezone.now() + timedelta(hours=2),
            estado='CONFIRMADO',
            motivo_reserva='Consulta general'
        )

        # Crear turno SIN médico
        self.turno_sin_medico = Turno.objects.create(
            paciente=self.paciente,
            medico=None,
            recurso=self.recurso,
            fecha_hora_inicio=timezone.now() + timedelta(hours=3),
            fecha_hora_fin=timezone.now() + timedelta(hours=4),
            estado='CONFIRMADO',
            motivo_reserva='Consulta sin médico'
        )

        # Autenticar como médico
        self.client.force_authenticate(user=self.user_medico)

    def test_crear_atencion_con_turno_con_medico_ok(self):
        """
        Crear Atención desde Turno con médico asignado → OK.
        El medico_principal se resuelve automáticamente desde el turno.
        """
        url = reverse('atenciones-list')
        data = {'turno': self.turno_con_medico.id}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar que se creó la atención
        atencion = Atencion.objects.get(turno=self.turno_con_medico)
        
        # Verificar que medico_principal se resolvió desde el turno
        self.assertEqual(atencion.medico_principal, self.medico)
        self.assertEqual(atencion.medico_principal_id, self.medico.id)
        self.assertIsNotNone(atencion.medico_principal_id)
        
        # Verificar otros campos
        self.assertEqual(atencion.paciente, self.paciente)
        self.assertEqual(atencion.tipo_atencion, Recurso.TipoRecurso.CONSULTORIO)
        self.assertEqual(atencion.estado_clinico, Atencion.EstadoClinico.ABIERTA)

    def test_crear_atencion_sin_turno_falla(self):
        """
        Crear Atención sin especificar turno → 400 con mensaje claro.
        """
        url = reverse('atenciones-list')
        data = {}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('turno', response.data['error'].lower())

    def test_crear_atencion_turno_sin_medico_falla(self):
        """
        Crear Atención desde Turno sin médico → 400 con mensaje claro.
        """
        url = reverse('atenciones-list')
        data = {'turno': self.turno_sin_medico.id}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('médico', response.data['error'].lower())

    def test_crear_atencion_turno_inexistente_falla(self):
        """
        Crear Atención con turno que no existe → 400.
        """
        url = reverse('atenciones-list')
        data = {'turno': 99999}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('no existe', response.data['error'].lower())

    def test_crear_atencion_idempotente(self):
        """
        Si ya existe una atención para el turno, retorna la existente (idempotencia).
        """
        url = reverse('atenciones-list')
        data = {'turno': self.turno_con_medico.id}

        # Primera llamada - crea la atención
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        atencion_id = response1.data['id']

        # Segunda llamada - retorna la existente
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['id'], atencion_id)

        # Verificar que solo hay una atención
        self.assertEqual(
            Atencion.objects.filter(turno=self.turno_con_medico).count(),
            1
        )

    def test_medico_principal_no_es_null_en_db(self):
        """
        Verificar que la fila en BD tiene medico_principal_id NOT NULL.
        """
        url = reverse('atenciones-list')
        data = {'turno': self.turno_con_medico.id}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verificar directamente en la BD
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT medico_principal_id FROM turnos_atencion WHERE id = %s",
                [response.data['id']]
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row[0], "medico_principal_id es NULL en la BD")

    def test_post_atencion_auditoria_en_alta_si_coherente_transaccion(self):
        """Una creación vía API genera un AuditEvent CREATE append-only.

        ``audit_service.log_event`` agenda la inserción vía
        ``transaction.on_commit`` cuando hay un atomic externo. ``TestCase``
        envuelve cada test en un atomic que nunca commitea, por eso usamos
        ``captureOnCommitCallbacks(execute=True)`` para forzar la ejecución
        de los callbacks dentro del scope.
        """
        url = reverse("atenciones-list")

        prior = AuditEvent.objects.filter(action="CREATE", entity_type="turnos.Atencion").count()
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                url, {"turno": self.turno_con_medico.id}, format="json"
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        nuevo = AuditEvent.objects.filter(action="CREATE", entity_type="turnos.Atencion").count()
        self.assertEqual(nuevo, prior + 1)

        prior2 = AuditEvent.objects.filter(action="CREATE", entity_type="turnos.Atencion").count()
        with self.captureOnCommitCallbacks(execute=True):
            resp2 = self.client.post(
                url, {"turno": self.turno_con_medico.id}, format="json"
            )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            AuditEvent.objects.filter(action="CREATE", entity_type="turnos.Atencion").count(),
            prior2,
        )















