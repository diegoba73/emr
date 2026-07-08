"""Permisos de turnos de estudio para médico y paciente (matriz QA-ROLE)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from django.test import TestCase
from rest_framework.test import APITestCase

from estudios.models import EstudioComplementario, TipoEstudioComplementario
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.access import medico_es_dueno_turno
from turnos.models import Atencion, Recurso, Turno

User = get_user_model()


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


def _sala(suffix: str) -> Recurso:
    return Recurso.objects.create(
        nombre=f'Sala est {suffix}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
        activo=True,
    )


def _consultorio(suffix: str) -> Recurso:
    return Recurso.objects.create(
        nombre=f'Cons {suffix}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )


def _turno_estudio(paciente, recurso, estudio, suffix: int) -> Turno:
    base = timezone.now().replace(second=0, microsecond=0) + timedelta(days=5, hours=suffix)
    turno = Turno.objects.create(
        paciente=paciente,
        medico=None,
        recurso=recurso,
        fecha_hora_inicio=base,
        fecha_hora_fin=base + timedelta(minutes=30),
        estado=Turno.Estado.RESERVADO,
        motivo_reserva=f'Estudio: {estudio.tipo_estudio.nombre}',
    )
    estudio.turno = turno
    estudio.estado = EstudioComplementario.Estado.CONFIRMADO
    estudio.save(update_fields=['turno', 'estado'])
    return turno


@pytest.mark.django_db
class TestMedicoEsDuenoTurnoUnit(TestCase):
    """``turnos.access.medico_es_dueno_turno`` — lógica pura."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Estudio access unit')
        cls.paciente = Paciente.objects.create(dni='TE-OWN-P', nombre='Pac', apellido='Own')
        cls.medico = Medico.objects.create(
            nombre='Dr',
            apellido='Own',
            matricula='TE-OWN-M',
            especialidad=cls.especialidad,
        )
        cls.medico_ajeno = Medico.objects.create(
            nombre='Dr',
            apellido='Ajeno',
            matricula='TE-OWN-A',
            especialidad=cls.especialidad,
        )
        cls.tipo = TipoEstudioComplementario.objects.create(
            nombre='Eco abdominal',
            modalidad=TipoEstudioComplementario.Modalidad.IMAGEN_US,
        )
        cls.sala = _sala('unit')
        cls.consultorio = _consultorio('unit')

    def test_medico_asignado_al_turno(self):
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.consultorio,
            fecha_hora_inicio=timezone.now() + timedelta(days=1),
            fecha_hora_fin=timezone.now() + timedelta(days=1, minutes=30),
            estado=Turno.Estado.RESERVADO,
        )
        assert medico_es_dueno_turno(self.medico, turno) is True
        assert medico_es_dueno_turno(self.medico_ajeno, turno) is False

    def test_medico_solicitante_estudio_sin_medico_en_turno(self):
        estudio = EstudioComplementario.objects.create(
            paciente=self.paciente,
            tipo_estudio=self.tipo,
            modalidad=self.tipo.modalidad,
            estado=EstudioComplementario.Estado.SOLICITADO,
            medico_solicitante=self.medico,
        )
        turno = _turno_estudio(self.paciente, self.sala, estudio, 1)
        assert medico_es_dueno_turno(self.medico, turno) is True
        assert medico_es_dueno_turno(self.medico_ajeno, turno) is False

    def test_medico_vinculado_por_atencion_previa(self):
        turno_cons = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.consultorio,
            fecha_hora_inicio=timezone.now(),
            fecha_hora_fin=timezone.now() + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        Atencion.objects.create(
            turno=turno_cons,
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        )
        estudio = EstudioComplementario.objects.create(
            paciente=self.paciente,
            tipo_estudio=self.tipo,
            modalidad=self.tipo.modalidad,
            estado=EstudioComplementario.Estado.SOLICITADO,
            medico_solicitante=None,
        )
        turno_est = _turno_estudio(self.paciente, self.sala, estudio, 2)
        assert medico_es_dueno_turno(self.medico, turno_est) is True
        assert medico_es_dueno_turno(self.medico_ajeno, turno_est) is False


@pytest.mark.django_db
class TestMedicoEstudioTurnoApi(APITestCase):
    """PATCH y acciones sobre turnos de estudio vía API."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Estudio API perm')
        cls.paciente = Paciente.objects.create(dni='TE-API-P', nombre='Pac', apellido='Api')
        cls.medico = Medico.objects.create(
            nombre='Dr',
            apellido='Api',
            matricula='TE-API-M',
            especialidad=cls.especialidad,
        )
        cls.medico_ajeno = Medico.objects.create(
            nombre='Dr',
            apellido='AjenoApi',
            matricula='TE-API-A',
            especialidad=cls.especialidad,
        )
        cls.tipo = TipoEstudioComplementario.objects.create(
            nombre='RX Tórax API',
            modalidad=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
        )
        cls.sala = _sala('api')
        cls.consultorio = _consultorio('api')
        turno_vinculo = Turno.objects.create(
            paciente=cls.paciente,
            medico=cls.medico,
            recurso=cls.consultorio,
            fecha_hora_inicio=timezone.now(),
            fecha_hora_fin=timezone.now() + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        Atencion.objects.create(
            turno=turno_vinculo,
            paciente=cls.paciente,
            medico_principal=cls.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        )
        cls.estudio = EstudioComplementario.objects.create(
            paciente=cls.paciente,
            tipo_estudio=cls.tipo,
            modalidad=cls.tipo.modalidad,
            estado=EstudioComplementario.Estado.SOLICITADO,
            medico_solicitante=cls.medico,
        )
        cls.turno_estudio = _turno_estudio(cls.paciente, cls.sala, cls.estudio, 3)

    def _auth_medico(self):
        user = User.objects.create_user(
            username='te_est_med',
            email='te_est_med@test.com',
            password='x',
            rol='medico',
        )
        self.medico.user = user
        self.medico.save()
        self.client.force_authenticate(user=user)
        return user

    def test_medico_solicitante_puede_patch_turno_estudio(self):
        self._auth_medico()
        r = self.client.patch(
            f'/api/turnos/{self.turno_estudio.id}/',
            {'motivo_reserva': 'Estudio: RX — actualizado por médico'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        self.turno_estudio.refresh_from_db()
        assert 'actualizado por médico' in self.turno_estudio.motivo_reserva

    def test_medico_solicitante_puede_confirmar_turno_estudio(self):
        self.turno_estudio.estado = Turno.Estado.RESERVADO
        self.turno_estudio.save(update_fields=['estado'])
        self._auth_medico()
        r = self.client.post(f'/api/turnos/{self.turno_estudio.id}/confirmar/')
        assert r.status_code == status.HTTP_200_OK
        self.turno_estudio.refresh_from_db()
        assert self.turno_estudio.estado == Turno.Estado.CONFIRMADO

    def test_medico_ajeno_no_puede_patch_turno_estudio(self):
        user = User.objects.create_user(
            username='te_est_med_no',
            email='te_est_med_no@test.com',
            password='x',
            rol='medico',
        )
        self.medico_ajeno.user = user
        self.medico_ajeno.save()
        self.client.force_authenticate(user=user)
        r = self.client.patch(
            f'/api/turnos/{self.turno_estudio.id}/',
            {'motivo_reserva': 'Intento ajeno estudio'},
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_paciente_puede_patch_turno_estudio_activo(self):
        user = User.objects.create_user(
            username='te_est_pac',
            email='te_est_pac@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        self.client.force_authenticate(user=user)
        r = self.client.patch(
            f'/api/turnos/{self.turno_estudio.id}/',
            {'motivo_reserva': 'Estudio: RX — paciente'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_paciente_no_puede_patch_turno_estudio_realizado(self):
        user = User.objects.create_user(
            username='te_est_pac_fin',
            email='te_est_pac_fin@test.com',
            password='x',
            rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        self.turno_estudio.estado = Turno.Estado.REALIZADO
        self.turno_estudio.save(update_fields=['estado'])
        self.client.force_authenticate(user=user)
        r = self.client.patch(
            f'/api/turnos/{self.turno_estudio.id}/',
            {'motivo_reserva': 'Intento post finalizado'},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSecretariaEstudiosSoloLectura(APITestCase):
    """Secretaría: lectura de estudios; sin creación ni PATCH."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Sec estudio RO')
        cls.paciente = Paciente.objects.create(dni='TE-SEC-P', nombre='Pac', apellido='Sec')
        cls.medico = Medico.objects.create(
            nombre='Dr',
            apellido='Sec',
            matricula='TE-SEC-M',
            especialidad=cls.especialidad,
        )
        cls.tipo = TipoEstudioComplementario.objects.create(
            nombre='TAC',
            modalidad=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
        )
        cls.estudio = EstudioComplementario.objects.create(
            paciente=cls.paciente,
            tipo_estudio=cls.tipo,
            modalidad=cls.tipo.modalidad,
            estado=EstudioComplementario.Estado.SOLICITADO,
            medico_solicitante=cls.medico,
        )

    def test_secretaria_lista_estudios(self):
        sec = User.objects.create_user(
            username='te_sec_list',
            email='te_sec_list@test.com',
            password='x',
            rol='secretaria',
        )
        self.client.force_authenticate(user=sec)
        r = self.client.get('/api/estudios-complementarios/')
        assert r.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in r.data.get('results', r.data)}
        assert self.estudio.id in ids

    def test_secretaria_no_crea_estudio(self):
        sec = User.objects.create_user(
            username='te_sec_crea',
            email='te_sec_crea@test.com',
            password='x',
            rol='secretaria',
        )
        self.client.force_authenticate(user=sec)
        r = self.client.post(
            '/api/estudios-complementarios/',
            {
                'paciente_id': self.paciente.id,
                'tipo_estudio': self.tipo.id,
                'modalidad': self.tipo.modalidad,
                'origen': 'INTERNO',
            },
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_secretaria_no_patch_estudio(self):
        sec = User.objects.create_user(
            username='te_sec_patch',
            email='te_sec_patch@test.com',
            password='x',
            rol='secretaria',
        )
        self.client.force_authenticate(user=sec)
        r = self.client.patch(
            f'/api/estudios-complementarios/{self.estudio.id}/',
            {'descripcion_clinica': 'Intento secretaría'},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN
