"""Tests de integración API para la app ``turnos``.

Convención local de seed:
- Especialidades con ``get_or_create`` y nombres con sufijo ``API`` para no
  pisar seeds compartidos.
- Pacientes con DNIs con prefijo ``TA-`` (Turnos API).
- Médicos con matrículas ``MTA-XXX``.
"""
import pytest
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from turnos.models import Recurso, Turno, Atencion
from pacientes.models import Paciente
from medicos.models import Especialidad, Medico

User = get_user_model()


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


@pytest.mark.django_db
class TestTurnoAPI(APITestCase):
    """Tests de integración para la API de Turnos."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='ta_admin',
            email='ta_admin@example.com',
            password='testpass123',
            rol='medico',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

        self.especialidad = _esp('Cardiología API')
        self.medico = Medico.objects.create(
            nombre='Dr. Test',
            apellido='Médico',
            matricula='MTA-001',
            especialidad=self.especialidad,
        )

        self.paciente = Paciente.objects.create(
            dni='TA-1001',
            nombre='Juan',
            apellido='Pérez',
        )

        self.recurso = Recurso.objects.create(
            nombre='Consultorio TA-1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

    def test_solapamiento_turnos(self):
        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        data = {
            'paciente_id': self.paciente.id,
            'medico_id': self.medico.id,
            'recurso_id': self.recurso.id,
            'fecha_hora_inicio': (fecha_base + timedelta(minutes=15)).isoformat(),
            'fecha_hora_fin': (fecha_base + timedelta(minutes=45)).isoformat(),
            'estado': Turno.Estado.RESERVADO,
        }
        response = self.client.post('/api/turnos/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_hora_inicio' in response.data or 'non_field_errors' in response.data

    def test_solapamiento_no_aplica_a_disponible(self):
        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        Turno.objects.create(
            paciente=None,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.DISPONIBLE,
        )

        data = {
            'paciente_id': self.paciente.id,
            'medico_id': self.medico.id,
            'recurso_id': self.recurso.id,
            'fecha_hora_inicio': (fecha_base + timedelta(minutes=15)).isoformat(),
            'fecha_hora_fin': (fecha_base + timedelta(minutes=45)).isoformat(),
            'estado': Turno.Estado.CONFIRMADO,
        }
        response = self.client.post('/api/turnos/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_filtro_fechas(self):
        fecha_enero = timezone.make_aware(datetime(2025, 1, 15, 10, 0, 0))
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_enero,
            fecha_hora_fin=fecha_enero + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        fecha_febrero = timezone.make_aware(datetime(2025, 2, 15, 10, 0, 0))
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_febrero,
            fecha_hora_fin=fecha_febrero + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        response = self.client.get('/api/turnos/?start=2025-01-01&end=2025-01-31')
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['fecha_hora_inicio'].startswith('2025-01')

    def test_permisos_paciente_solo_sus_turnos(self):
        paciente_a = Paciente.objects.create(
            dni='TA-1101',
            nombre='Paciente',
            apellido='A',
        )
        paciente_b = Paciente.objects.create(
            dni='TA-1102',
            nombre='Paciente',
            apellido='B',
        )
        user_a = User.objects.create_user(
            username='ta_paciente_a',
            email='ta_paciente_a@test.com',
            password='testpass123',
            rol='paciente',
        )
        paciente_a.user = user_a
        paciente_a.save()

        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        Turno.objects.create(
            paciente=paciente_a,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        Turno.objects.create(
            paciente=paciente_b,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base + timedelta(hours=1),
            fecha_hora_fin=fecha_base + timedelta(hours=1, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=user_a)
        response = self.client.get('/api/turnos/')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        # En lectura, ``paciente`` viene serializado como objeto anidado.
        paciente_field = results[0]['paciente']
        assert paciente_field is not None
        assert paciente_field['id'] == paciente_a.id

    def test_permisos_medico_ve_sus_turnos(self):
        medico_b = Medico.objects.create(
            nombre='Dr. B',
            apellido='Médico',
            matricula='MTA-002',
            especialidad=self.especialidad,
        )
        user_medico = User.objects.create_user(
            username='ta_medico',
            email='ta_medico@test.com',
            password='testpass123',
            rol='medico',
        )
        medico_b.user = user_medico
        medico_b.save()

        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        Turno.objects.create(
            paciente=self.paciente,
            medico=medico_b,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base + timedelta(hours=1),
            fecha_hora_fin=fecha_base + timedelta(hours=1, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=user_medico)
        response = self.client.get('/api/turnos/')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        medico_field = results[0]['medico']
        assert medico_field is not None
        assert medico_field['id'] == medico_b.id

    def test_medico_all_true_no_escala(self):
        """``?all=true`` no debe convertir a un médico en lector de agenda global."""
        medico_b = Medico.objects.create(
            nombre='Dr. B',
            apellido='Médico',
            matricula='MTA-003',
            especialidad=self.especialidad,
        )
        user_medico = User.objects.create_user(
            username='ta_medico_all',
            email='ta_medico_all@test.com',
            password='testpass123',
            rol='medico',
        )
        medico_b.user = user_medico
        medico_b.save()

        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        turno_propio = Turno.objects.create(
            paciente=self.paciente,
            medico=medico_b,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base + timedelta(hours=1),
            fecha_hora_fin=fecha_base + timedelta(hours=1, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=user_medico)
        response = self.client.get('/api/turnos/?all=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == turno_propio.id

    def test_medico_sin_ficha_medico_ve_vacio(self):
        user_sin_ficha = User.objects.create_user(
            username='ta_medico_sin_ficha',
            email='ta_medico_sin_ficha@test.com',
            password='testpass123',
            rol='medico',
        )
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=timezone.now() + timedelta(days=1),
            fecha_hora_fin=timezone.now() + timedelta(days=1, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=user_sin_ficha)
        for url in ('/api/turnos/', '/api/turnos/?all=true'):
            response = self.client.get(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['results'] == []

    def test_medico_no_puede_retrieve_turno_ajeno_con_all_true(self):
        medico_b = Medico.objects.create(
            nombre='Dr. Ajeno',
            apellido='Retrieve',
            matricula='MTA-004',
            especialidad=self.especialidad,
        )
        user_medico = User.objects.create_user(
            username='ta_medico_retrieve',
            email='ta_medico_retrieve@test.com',
            password='testpass123',
            rol='medico',
        )
        medico_b.user = user_medico
        medico_b.save()

        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        turno_ajeno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=user_medico)
        response = self.client.get(f'/api/turnos/{turno_ajeno.id}/?all=true')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_medico_no_puede_patch_turno_ajeno_con_all_true(self):
        medico_b = Medico.objects.create(
            nombre='Dr. Ajeno',
            apellido='Patch',
            matricula='MTA-005',
            especialidad=self.especialidad,
        )
        user_medico = User.objects.create_user(
            username='ta_medico_patch',
            email='ta_medico_patch@test.com',
            password='testpass123',
            rol='medico',
        )
        medico_b.user = user_medico
        medico_b.save()

        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        turno_ajeno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=user_medico)
        response = self.client.patch(
            f'/api/turnos/{turno_ajeno.id}/?all=true',
            {'motivo_reserva': 'intento'},
            format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        turno_ajeno.refresh_from_db()
        assert turno_ajeno.motivo_reserva != 'intento'

    def test_secretaria_ve_agenda_global_con_y_sin_all_true(self):
        secretaria = User.objects.create_user(
            username='ta_secretaria_turnos',
            email='ta_secretaria@test.com',
            password='testpass123',
            rol='secretaria',
        )
        medico_b = Medico.objects.create(
            nombre='Dr. B',
            apellido='Sec',
            matricula='MTA-006',
            especialidad=self.especialidad,
        )
        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        Turno.objects.create(
            paciente=self.paciente,
            medico=medico_b,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base + timedelta(hours=1),
            fecha_hora_fin=fecha_base + timedelta(hours=1, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=secretaria)
        for url in ('/api/turnos/', '/api/turnos/?all=true'):
            response = self.client.get(url)
            assert response.status_code == status.HTTP_200_OK
            assert len(response.data['results']) == 2

    def test_laboratorio_no_ve_turnos(self):
        lab_user = User.objects.create_user(
            username='ta_laboratorio_turnos',
            email='ta_lab@test.com',
            password='testpass123',
            rol='laboratorio',
        )
        Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=timezone.now() + timedelta(days=2),
            fecha_hora_fin=timezone.now() + timedelta(days=2, minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        self.client.force_authenticate(user=lab_user)
        response = self.client.get('/api/turnos/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []

    def test_validacion_fecha_fin_mayor_inicio(self):
        fecha_base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        data = {
            'paciente_id': self.paciente.id,
            'medico_id': self.medico.id,
            'recurso_id': self.recurso.id,
            'fecha_hora_inicio': fecha_base.isoformat(),
            'fecha_hora_fin': (fecha_base - timedelta(minutes=30)).isoformat(),
            'estado': Turno.Estado.CONFIRMADO,
        }
        response = self.client.post('/api/turnos/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_hora_fin' in response.data

    def test_delete_turno_bloqueado(self):
        """DELETE físico de Turno debe responder 405 MethodNotAllowed."""
        fecha_base = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

        response = self.client.delete(f'/api/turnos/{turno.id}/')

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Turno.objects.filter(pk=turno.id).exists()


@pytest.mark.django_db
class TestAtencionDeleteAPI(APITestCase):
    """DELETE físico de Atencion debe estar bloqueado."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='ta_admin_atencion',
            email='ta_admin_at@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.admin)

        self.especialidad = _esp('Cardiología API Atencion')
        self.medico = Medico.objects.create(
            matricula='MTA-100',
            nombre='Doc',
            apellido='Atencion',
            especialidad=self.especialidad,
        )
        self.paciente = Paciente.objects.create(
            dni='TA-9001',
            nombre='Pac',
            apellido='Atencion',
        )
        self.atencion = Atencion.objects.create(
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )

    def test_delete_atencion_bloqueado(self):
        response = self.client.delete(f'/api/atenciones/{self.atencion.id}/')

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Atencion.objects.filter(pk=self.atencion.id).exists()


@pytest.mark.django_db
class TestRecursoSoftDeleteAPI(APITestCase):
    """DELETE de Recurso debe ser baja lógica (``activo=False``), no físico."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='ta_admin_recurso',
            email='ta_admin_recurso@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.admin)

        self.recurso = Recurso.objects.create(
            nombre='Consultorio TA-Soft-1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        self.paciente = Paciente.objects.create(
            dni='TA-9101',
            nombre='Hist',
            apellido='Soft',
        )

        # Turno histórico que NO debe perderse al "borrar" el recurso vía API.
        fecha_base = timezone.now() + timedelta(days=2)
        self.turno_historico = Turno.objects.create(
            paciente=self.paciente,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_base,
            fecha_hora_fin=fecha_base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )

    def test_destroy_es_soft_delete(self):
        response = self.client.delete(f'/api/recursos/{self.recurso.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # El recurso sigue existiendo físicamente, pero como inactivo.
        self.recurso.refresh_from_db()
        assert self.recurso.activo is False
        # El turno histórico se conserva (no hay cascada destructiva).
        assert Turno.objects.filter(pk=self.turno_historico.id).exists()

    def test_destroy_soft_delete_idempotente(self):
        self.recurso.activo = False
        self.recurso.save(update_fields=['activo'])

        response = self.client.delete(f'/api/recursos/{self.recurso.id}/')
        # El recurso ya no aparece en el queryset (filtra activo=True), por
        # lo que el detail-route devuelve 404, lo cual es comportamiento
        # esperado en DRF para entidades no listables.
        assert response.status_code in (status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND)
        self.recurso.refresh_from_db()
        assert self.recurso.activo is False

    def test_no_admin_no_puede_dar_de_baja(self):
        non_admin = User.objects.create_user(
            username='ta_not_admin_recurso',
            email='ta_not_admin@test.com',
            password='x',
            rol='medico',
        )
        self.client.force_authenticate(user=non_admin)
        response = self.client.delete(f'/api/recursos/{self.recurso.id}/')

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
        self.recurso.refresh_from_db()
        assert self.recurso.activo is True
