"""Permisos de creación y modificación en ``/api/turnos/`` (C5.8.1)."""
from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno

User = get_user_model()


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


def _recurso(suffix: str) -> Recurso:
    return Recurso.objects.create(
        nombre=f'Cons Mut {suffix}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )


def _turno_payload(paciente, medico, recurso, offset_hours=48):
    base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=offset_hours)
    return {
        'paciente_id': paciente.id,
        'medico_id': medico.id,
        'recurso_id': recurso.id,
        'fecha_hora_inicio': base.isoformat(),
        'fecha_hora_fin': (base + timedelta(minutes=30)).isoformat(),
        'estado': Turno.Estado.RESERVADO,
        'motivo_reserva': 'Mutación API',
    }


@pytest.mark.django_db
class TestTurnoCreatePermissions(APITestCase):
    """POST /api/turnos/ por rol."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Mut API')
        cls.paciente_a = Paciente.objects.create(
            dni='TA-MUT-A',
            nombre='Paciente',
            apellido='A',
        )
        cls.paciente_b = Paciente.objects.create(
            dni='TA-MUT-B',
            nombre='Paciente',
            apellido='B',
        )
        cls.medico_a = Medico.objects.create(
            nombre='Dr',
            apellido='A',
            matricula='MTA-MUT-A',
            especialidad=cls.especialidad,
        )
        cls.medico_b = Medico.objects.create(
            nombre='Dr',
            apellido='B',
            matricula='MTA-MUT-B',
            especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('base')

    def test_admin_puede_crear_turno(self):
        admin = User.objects.create_user(
            username='ta_mut_admin',
            email='ta_mut_admin@test.com',
            password='x',
            rol='admin',
        )
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_a, self.recurso, 50),
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['medico']['id'] == self.medico_a.id

    def test_secretaria_puede_crear_turno(self):
        sec = User.objects.create_user(
            username='ta_mut_sec',
            email='ta_mut_sec@test.com',
            password='x',
            rol='secretaria',
        )
        self.client.force_authenticate(user=sec)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_b, self.recurso, 51),
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_enfermeria_no_puede_crear_turno(self):
        enf = User.objects.create_user(
            username='ta_mut_enf',
            email='ta_mut_enf@test.com',
            password='x',
            rol='enfermeria',
        )
        self.client.force_authenticate(user=enf)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_a, self.recurso, 52),
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_medico_crea_turno_forzado_a_si_mismo(self):
        user = User.objects.create_user(
            username='ta_mut_med_own',
            email='ta_mut_med_own@test.com',
            password='x',
            rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_a, self.recurso, 53),
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['medico']['id'] == self.medico_a.id

    def test_medico_no_puede_crear_turno_para_otro_medico(self):
        user = User.objects.create_user(
            username='ta_mut_med_other',
            email='ta_mut_med_other@test.com',
            password='x',
            rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        self.client.force_authenticate(user=user)
        payload = _turno_payload(self.paciente_a, self.medico_b, self.recurso, 54)
        response = self.client.post('/api/turnos/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['medico']['id'] == self.medico_a.id
        assert response.data['medico']['id'] != self.medico_b.id

    def test_medico_sin_ficha_no_puede_crear_turno(self):
        user = User.objects.create_user(
            username='ta_mut_med_noficha',
            email='ta_mut_med_noficha@test.com',
            password='x',
            rol='medico',
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_a, self.recurso, 55),
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_crea_turno_forzado_a_si_mismo(self):
        user = User.objects.create_user(
            username='ta_mut_pac_own',
            email='ta_mut_pac_own@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        self.client.force_authenticate(user=user)
        payload = _turno_payload(self.paciente_b, self.medico_a, self.recurso, 56)
        response = self.client.post('/api/turnos/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['paciente']['id'] == self.paciente_a.id

    def test_paciente_no_puede_crear_turno_para_otro_paciente(self):
        user = User.objects.create_user(
            username='ta_mut_pac_other',
            email='ta_mut_pac_other@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        self.client.force_authenticate(user=user)
        payload = _turno_payload(self.paciente_b, self.medico_a, self.recurso, 57)
        response = self.client.post('/api/turnos/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['paciente']['id'] == self.paciente_a.id
        assert response.data['paciente']['id'] != self.paciente_b.id

    def test_laboratorio_no_puede_crear_turno(self):
        lab = User.objects.create_user(
            username='ta_mut_lab',
            email='ta_mut_lab@test.com',
            password='x',
            rol='laboratorio',
        )
        self.client.force_authenticate(user=lab)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_a, self.recurso, 58),
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_usuario_sin_rol_no_puede_crear_turno(self):
        user = User.objects.create_user(
            username='ta_mut_norol',
            email='ta_mut_norol@test.com',
            password='x',
            rol='rol_desconocido',
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/api/turnos/',
            _turno_payload(self.paciente_a, self.medico_a, self.recurso, 59),
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTurnoPatchPermissions(APITestCase):
    """PATCH /api/turnos/{id}/ por rol."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Mut Patch')
        cls.paciente_a = Paciente.objects.create(
            dni='TA-MUT-PA',
            nombre='Paciente',
            apellido='PatchA',
        )
        cls.paciente_b = Paciente.objects.create(
            dni='TA-MUT-PB',
            nombre='Paciente',
            apellido='PatchB',
        )
        cls.medico_a = Medico.objects.create(
            nombre='Dr',
            apellido='PatchA',
            matricula='MTA-MUT-PA',
            especialidad=cls.especialidad,
        )
        cls.medico_b = Medico.objects.create(
            nombre='Dr',
            apellido='PatchB',
            matricula='MTA-MUT-PB',
            especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('patch')

    def _turno(self, paciente, medico, suffix):
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(days=3, hours=suffix)
        return Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )

    def test_medico_puede_patch_turno_propio(self):
        user = User.objects.create_user(
            username='ta_mut_patch_med_ok',
            email='ta_mut_patch_med_ok@test.com',
            password='x',
            rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.paciente_a, self.medico_a, 1)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Actualizado por médico'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.motivo_reserva == 'Actualizado por médico'

    def test_medico_no_puede_patch_turno_ajeno(self):
        user = User.objects.create_user(
            username='ta_mut_patch_med_no',
            email='ta_mut_patch_med_no@test.com',
            password='x',
            rol='medico',
        )
        self.medico_b.user = user
        self.medico_b.save()
        turno = self._turno(self.paciente_a, self.medico_a, 2)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Intento ajeno'},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_medico_no_puede_reasignar_turno_a_otro_medico(self):
        user = User.objects.create_user(
            username='ta_mut_patch_reasign',
            email='ta_mut_patch_reasign@test.com',
            password='x',
            rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.paciente_a, self.medico_a, 3)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'medico_id': self.medico_b.id},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        turno.refresh_from_db()
        assert turno.medico_id == self.medico_a.id

    def test_paciente_puede_patch_turno_propio(self):
        user = User.objects.create_user(
            username='ta_mut_patch_pac_ok',
            email='ta_mut_patch_pac_ok@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        turno = self._turno(self.paciente_a, self.medico_a, 4)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Paciente actualiza'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_paciente_no_puede_patch_turno_ajeno(self):
        user = User.objects.create_user(
            username='ta_mut_patch_pac_no',
            email='ta_mut_patch_pac_no@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        turno = self._turno(self.paciente_b, self.medico_a, 5)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Intento ajeno paciente'},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_paciente_no_puede_reasignar_paciente(self):
        user = User.objects.create_user(
            username='ta_mut_patch_pac_reasign',
            email='ta_mut_patch_pac_reasign@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        turno = self._turno(self.paciente_a, self.medico_a, 6)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'paciente_id': self.paciente_b.id},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        turno.refresh_from_db()
        assert turno.paciente_id == self.paciente_a.id

    def test_secretaria_puede_patch_global(self):
        sec = User.objects.create_user(
            username='ta_mut_patch_sec',
            email='ta_mut_patch_sec@test.com',
            password='x',
            rol='secretaria',
        )
        turno = self._turno(self.paciente_a, self.medico_a, 7)
        self.client.force_authenticate(user=sec)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Secretaría global'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_enfermeria_no_puede_patch(self):
        enf = User.objects.create_user(
            username='ta_mut_patch_enf',
            email='ta_mut_patch_enf@test.com',
            password='x',
            rol='enfermeria',
        )
        turno = self._turno(self.paciente_a, self.medico_a, 8)
        self.client.force_authenticate(user=enf)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Enfermería'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_patch(self):
        lab = User.objects.create_user(
            username='ta_mut_patch_lab',
            email='ta_mut_patch_lab@test.com',
            password='x',
            rol='laboratorio',
        )
        turno = self._turno(self.paciente_a, self.medico_a, 9)
        self.client.force_authenticate(user=lab)
        response = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'motivo_reserva': 'Lab'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
