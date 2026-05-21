"""Acciones de estado de turno y bloqueo PATCH/PUT estado (C5.9.1 / C5.9.2)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from auditoria.models import AuditEvent
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno

User = get_user_model()


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


def _recurso(suffix: str) -> Recurso:
    return Recurso.objects.create(
        nombre=f'Cons Estado {suffix}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )


@pytest.mark.django_db
class TestConfirmarTurno(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Estado')
        cls.paciente = Paciente.objects.create(
            dni='TE-CONF-1', nombre='Pac', apellido='Conf',
        )
        cls.medico_a = Medico.objects.create(
            nombre='Dr', apellido='A', matricula='TE-MA', especialidad=cls.especialidad,
        )
        cls.medico_b = Medico.objects.create(
            nombre='Dr', apellido='B', matricula='TE-MB', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('conf')

    def _turno_reservado(self, medico, suffix: int) -> Turno:
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=48 + suffix)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )

    def test_secretaria_puede_confirmar(self):
        sec = User.objects.create_user(
            username='te_conf_sec', email='te_conf_sec@test.com', password='x', rol='secretaria',
        )
        turno = self._turno_reservado(self.medico_a, 1)
        self.client.force_authenticate(user=sec)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert r.data['applied'] is True
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.CONFIRMADO

    def test_medico_propio_puede_confirmar(self):
        user = User.objects.create_user(
            username='te_conf_med', email='te_conf_med@test.com', password='x', rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno_reservado(self.medico_a, 2)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.CONFIRMADO

    def test_medico_ajeno_no_puede_confirmar(self):
        user = User.objects.create_user(
            username='te_conf_med_no', email='te_conf_med_no@test.com', password='x', rol='medico',
        )
        self.medico_b.user = user
        self.medico_b.save()
        turno = self._turno_reservado(self.medico_a, 3)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_paciente_no_puede_confirmar(self):
        user = User.objects.create_user(
            username='te_conf_pac', email='te_conf_pac@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        turno = self._turno_reservado(self.medico_a, 4)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_enfermeria_no_puede_confirmar(self):
        enf = User.objects.create_user(
            username='te_conf_enf', email='te_conf_enf@test.com', password='x', rol='enfermeria',
        )
        turno = self._turno_reservado(self.medico_a, 5)
        self.client.force_authenticate(user=enf)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_confirmar(self):
        lab = User.objects.create_user(
            username='te_conf_lab', email='te_conf_lab@test.com', password='x', rol='laboratorio',
        )
        turno = self._turno_reservado(self.medico_a, 6)
        self.client.force_authenticate(user=lab)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_confirmar_desde_cancelado_400(self):
        admin = User.objects.create_user(
            username='te_conf_adm', email='te_conf_adm@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=60)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico_a,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.CANCELADO,
        )
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirmar_desde_realizado_400(self):
        admin = User.objects.create_user(
            username='te_conf_adm2', email='te_conf_adm2@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=61)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico_a,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.REALIZADO,
        )
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirmar_idempotente(self):
        admin = User.objects.create_user(
            username='te_conf_idem', email='te_conf_idem@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=62)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico_a,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert r.data['applied'] is False
        assert 'ya está confirmado' in r.data['message'].lower()


@pytest.mark.django_db
class TestCancelarTurno(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Cancel')
        cls.paciente_a = Paciente.objects.create(
            dni='TE-CAN-A', nombre='Pac', apellido='A',
        )
        cls.paciente_b = Paciente.objects.create(
            dni='TE-CAN-B', nombre='Pac', apellido='B',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Can', matricula='TE-CAN-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('can')

    def _turno(self, paciente, estado, suffix: int) -> Turno:
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=80 + suffix)
        return Turno.objects.create(
            paciente=paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=estado,
        )

    def test_secretaria_puede_cancelar_confirmado(self):
        sec = User.objects.create_user(
            username='te_can_sec', email='te_can_sec@test.com', password='x', rol='secretaria',
        )
        turno = self._turno(self.paciente_a, Turno.Estado.CONFIRMADO, 1)
        self.client.force_authenticate(user=sec)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'Paciente no asiste'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.CANCELADO

    def test_medico_propio_puede_cancelar(self):
        user = User.objects.create_user(
            username='te_can_med', email='te_can_med@test.com', password='x', rol='medico',
        )
        self.medico.user = user
        self.medico.save()
        turno = self._turno(self.paciente_a, Turno.Estado.RESERVADO, 2)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'Reagenda'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_paciente_propio_puede_cancelar(self):
        user = User.objects.create_user(
            username='te_can_pac', email='te_can_pac@test.com', password='x', rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        turno = self._turno(self.paciente_a, Turno.Estado.RESERVADO, 3)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'No puedo asistir'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_medico_ajeno_no_puede_cancelar(self):
        medico_b = Medico.objects.create(
            nombre='Dr', apellido='B2', matricula='TE-CAN-MB2', especialidad=self.especialidad,
        )
        user = User.objects.create_user(
            username='te_can_med_no', email='te_can_med_no@test.com', password='x', rol='medico',
        )
        medico_b.user = user
        medico_b.save()
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=84)
        turno = Turno.objects.create(
            paciente=self.paciente_a,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'X'},
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_paciente_ajeno_no_puede_cancelar(self):
        user = User.objects.create_user(
            username='te_can_pac_no', email='te_can_pac_no@test.com', password='x', rol='paciente',
        )
        self.paciente_a.user = user
        self.paciente_a.save()
        turno = self._turno(self.paciente_b, Turno.Estado.RESERVADO, 5)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'X'},
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_enfermeria_no_puede_cancelar(self):
        enf = User.objects.create_user(
            username='te_can_enf', email='te_can_enf@test.com', password='x', rol='enfermeria',
        )
        turno = self._turno(self.paciente_a, Turno.Estado.RESERVADO, 6)
        self.client.force_authenticate(user=enf)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'X'},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_cancelar_sin_motivo_400(self):
        admin = User.objects.create_user(
            username='te_can_nomot', email='te_can_nomot@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.paciente_a, Turno.Estado.RESERVADO, 7)
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/cancelar/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancelar_realizado_400(self):
        admin = User.objects.create_user(
            username='te_can_real', email='te_can_real@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.paciente_a, Turno.Estado.REALIZADO, 8)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'Tarde'},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancelar_idempotente(self):
        admin = User.objects.create_user(
            username='te_can_idem', email='te_can_idem@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.paciente_a, Turno.Estado.CANCELADO, 9)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'Otra vez'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.data['applied'] is False


@pytest.mark.django_db
class TestPatchEstadoBloqueado(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Patch Est')
        cls.paciente = Paciente.objects.create(
            dni='TE-PATCH-P', nombre='Pac', apellido='Patch',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Patch', matricula='TE-PATCH-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('patch')

    def _turno(self) -> Turno:
        base = timezone.now() + timedelta(hours=100)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )

    def test_medico_no_puede_patch_estado(self):
        user = User.objects.create_user(
            username='te_patch_med', email='te_patch_med@test.com', password='x', rol='medico',
        )
        self.medico.user = user
        self.medico.save()
        turno = self._turno()
        self.client.force_authenticate(user=user)
        r = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'estado': Turno.Estado.CONFIRMADO},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado' in r.data
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO

    def test_paciente_no_puede_patch_estado(self):
        user = User.objects.create_user(
            username='te_patch_pac', email='te_patch_pac@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        turno = self._turno()
        self.client.force_authenticate(user=user)
        r = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'estado': Turno.Estado.CANCELADO},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_secretaria_no_puede_patch_estado_directo(self):
        sec = User.objects.create_user(
            username='te_patch_sec', email='te_patch_sec@test.com', password='x', rol='secretaria',
        )
        turno = self._turno()
        self.client.force_authenticate(user=sec)
        r = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'estado': Turno.Estado.CONFIRMADO},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado' in r.data
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO

    def test_admin_no_puede_patch_estado_directo(self):
        admin = User.objects.create_user(
            username='te_patch_adm', email='te_patch_adm@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno()
        self.client.force_authenticate(user=admin)
        r = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'estado': Turno.Estado.CONFIRMADO},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_staff_no_puede_patch_estado_directo(self):
        staff = User.objects.create_user(
            username='te_patch_stf', email='te_patch_stf@test.com', password='x',
            is_staff=True,
        )
        turno = self._turno()
        self.client.force_authenticate(user=staff)
        r = self.client.patch(
            f'/api/turnos/{turno.id}/',
            {'estado': Turno.Estado.CANCELADO},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAuditoriaTransicionTurno(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Audit T')
        cls.paciente = Paciente.objects.create(
            dni='TE-AUD', nombre='Pac', apellido='Aud',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Aud', matricula='TE-AUD-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('aud')

    def test_confirmar_auditoria_metadata(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_aud_conf', email='te_aud_conf@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=120)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )
        self.client.force_authenticate(user=admin)
        with capture_on_commit_callbacks(execute=True):
            self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')

        ev = (
            AuditEvent.objects.filter(
                entity_type='turnos.Turno',
                entity_id=str(turno.id),
                action='UPDATE',
            )
            .order_by('-id')
            .first()
        )
        assert ev is not None
        assert ev.actor_id == admin.id
        assert ev.before_state is not None
        assert ev.after_state is not None
        assert ev.before_state.get('estado') == Turno.Estado.RESERVADO
        assert ev.after_state.get('estado') == Turno.Estado.CONFIRMADO
        assert ev.metadata.get('accion') == 'confirmar_turno'
        assert ev.metadata.get('estado_anterior') == Turno.Estado.RESERVADO
        assert ev.metadata.get('estado_nuevo') == Turno.Estado.CONFIRMADO
        assert ev.metadata.get('turno_id') == turno.id
        assert ev.metadata.get('view') == 'TurnoViewSet.confirmar'

    def test_cancelar_auditoria_con_motivo(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_aud_can', email='te_aud_can@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=121)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        self.client.force_authenticate(user=admin)
        with capture_on_commit_callbacks(execute=True):
            self.client.post(
                f'/api/turnos/{turno.id}/cancelar/',
                {'motivo': 'Motivo prueba auditoría'},
                format='json',
            )

        ev = (
            AuditEvent.objects.filter(
                entity_type='turnos.Turno',
                entity_id=str(turno.id),
                action='UPDATE',
            )
            .order_by('-id')
            .first()
        )
        assert ev is not None
        assert ev.actor_id == admin.id
        assert ev.before_state.get('estado') == Turno.Estado.CONFIRMADO
        assert ev.after_state.get('estado') == Turno.Estado.CANCELADO
        assert ev.metadata.get('accion') == 'cancelar_turno'
        assert ev.metadata.get('motivo') == 'Motivo prueba auditoría'
        assert ev.metadata.get('estado_anterior') == Turno.Estado.CONFIRMADO
        assert ev.metadata.get('estado_nuevo') == Turno.Estado.CANCELADO
        assert ev.metadata.get('turno_id') == turno.id
        assert ev.metadata.get('view') == 'TurnoViewSet.cancelar'


def _audit_update_count(turno_id: int) -> int:
    return AuditEvent.objects.filter(
        entity_type='turnos.Turno',
        entity_id=str(turno_id),
        action='UPDATE',
    ).count()


@pytest.mark.django_db
class TestPutEstadoBloqueado(APITestCase):
    """PUT completo también pasa por ``_reject_direct_estado_change``."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología PUT Est')
        cls.paciente = Paciente.objects.create(
            dni='TE-PUT-P', nombre='Pac', apellido='Put',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Put', matricula='TE-PUT-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('put')

    def _turno(self) -> Turno:
        base = timezone.now() + timedelta(hours=130)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )

    def _put_payload(self, turno: Turno, estado: str) -> dict:
        return {
            'paciente_id': turno.paciente_id,
            'medico_id': turno.medico_id,
            'recurso_id': turno.recurso_id,
            'fecha_hora_inicio': turno.fecha_hora_inicio.isoformat(),
            'fecha_hora_fin': turno.fecha_hora_fin.isoformat(),
            'estado': estado,
            'motivo_reserva': turno.motivo_reserva or '',
        }

    def test_medico_no_puede_put_estado_directo(self):
        user = User.objects.create_user(
            username='te_put_med', email='te_put_med@test.com', password='x', rol='medico',
        )
        self.medico.user = user
        self.medico.save()
        turno = self._turno()
        self.client.force_authenticate(user=user)
        r = self.client.put(
            f'/api/turnos/{turno.id}/',
            self._put_payload(turno, Turno.Estado.CONFIRMADO),
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado' in r.data
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO

    def test_paciente_no_puede_put_estado_directo(self):
        user = User.objects.create_user(
            username='te_put_pac', email='te_put_pac@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        turno = self._turno()
        self.client.force_authenticate(user=user)
        r = self.client.put(
            f'/api/turnos/{turno.id}/',
            self._put_payload(turno, Turno.Estado.CANCELADO),
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO


@pytest.mark.django_db
class TestIdempotenciaSinAuditoriaDuplicada(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Idem Aud')
        cls.paciente = Paciente.objects.create(
            dni='TE-IDEM-A', nombre='Pac', apellido='Idem',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Idem', matricula='TE-IDEM-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('idem')

    def test_confirmar_idempotente_no_duplica_auditoria(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_idem_conf_aud', email='te_idem_conf_aud@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=140)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.CONFIRMADO,
        )
        self.client.force_authenticate(user=admin)
        n_before = _audit_update_count(turno.id)
        with capture_on_commit_callbacks(execute=True):
            r = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert r.data['applied'] is False
        assert _audit_update_count(turno.id) == n_before

    def test_cancelar_idempotente_no_duplica_auditoria(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_idem_can_aud', email='te_idem_can_aud@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=141)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.CANCELADO,
        )
        self.client.force_authenticate(user=admin)
        n_before = _audit_update_count(turno.id)
        with capture_on_commit_callbacks(execute=True):
            r = self.client.post(
                f'/api/turnos/{turno.id}/cancelar/',
                {'motivo': 'Reintento'},
                format='json',
            )
        assert r.status_code == status.HTTP_200_OK
        assert r.data['applied'] is False
        assert _audit_update_count(turno.id) == n_before


@pytest.mark.django_db
class TestLaboratorioCancelarTurno(APITestCase):
    """Laboratorio: queryset vacío → 404 al cancelar (ocultamiento por rol)."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Lab Can')
        cls.paciente = Paciente.objects.create(
            dni='TE-LAB-CAN', nombre='Pac', apellido='Lab',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Lab', matricula='TE-LAB-CAN-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('labc')

    def test_laboratorio_no_puede_cancelar(self):
        lab = User.objects.create_user(
            username='te_lab_can', email='te_lab_can@test.com', password='x', rol='laboratorio',
        )
        base = timezone.now() + timedelta(hours=150)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )
        self.client.force_authenticate(user=lab)
        r = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'Intento lab'},
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO


@pytest.mark.django_db
class TestUsuarioSinRolAccionesTurno(APITestCase):
    """Usuario autenticado sin rol de gestión ni vínculo médico/paciente útil."""

    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Sin Rol')
        cls.paciente = Paciente.objects.create(
            dni='TE-NOROL-P', nombre='Pac', apellido='Norol',
        )
        cls.medico = Medico.objects.create(
            nombre='Dr', apellido='Norol', matricula='TE-NOROL-M', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('norol')

    def _turno(self) -> Turno:
        base = timezone.now() + timedelta(hours=160)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )

    def test_usuario_sin_rol_no_puede_confirmar_ni_cancelar(self):
        user = User.objects.create_user(
            username='te_norol', email='te_norol@test.com', password='x', rol='',
        )
        turno = self._turno()
        self.client.force_authenticate(user=user)

        r_conf = self.client.post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
        assert r_conf.status_code == status.HTTP_404_NOT_FOUND

        r_can = self.client.post(
            f'/api/turnos/{turno.id}/cancelar/',
            {'motivo': 'X'},
            format='json',
        )
        assert r_can.status_code == status.HTTP_404_NOT_FOUND

        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO


@pytest.mark.django_db
class TestReprogramarTurno(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Reprog')
        cls.paciente = Paciente.objects.create(
            dni='TE-REP-P', nombre='Pac', apellido='Rep',
        )
        cls.medico_a = Medico.objects.create(
            nombre='Dr', apellido='RepA', matricula='TE-REP-A', especialidad=cls.especialidad,
        )
        cls.medico_b = Medico.objects.create(
            nombre='Dr', apellido='RepB', matricula='TE-REP-B', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('rep')
        cls.recurso_b = Recurso.objects.create(
            nombre='Cons Reprog B',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

    def _turno(self, medico, estado, offset_hours: int) -> Turno:
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=200 + offset_hours)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=estado,
        )

    def _payload_reprog(self, turno: Turno, inicio, fin, **extra) -> dict:
        data = {
            'fecha_hora_inicio': inicio.isoformat(),
            'fecha_hora_fin': fin.isoformat(),
            'motivo': 'Reprogramación de prueba',
        }
        data.update(extra)
        return data

    def test_secretaria_puede_reprogramar_reservado(self):
        sec = User.objects.create_user(
            username='te_rep_sec', email='te_rep_sec@test.com', password='x', rol='secretaria',
        )
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 1)
        nuevo_inicio = turno.fecha_hora_inicio + timedelta(days=2)
        nuevo_fin = nuevo_inicio + timedelta(minutes=30)
        self.client.force_authenticate(user=sec)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(turno, nuevo_inicio, nuevo_fin),
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.RESERVADO
        assert turno.fecha_hora_inicio == nuevo_inicio

    def test_medico_propio_puede_reprogramar_sin_cambiar_medico(self):
        user = User.objects.create_user(
            username='te_rep_med', email='te_rep_med@test.com', password='x', rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 2)
        nuevo_inicio = turno.fecha_hora_inicio + timedelta(days=1)
        nuevo_fin = nuevo_inicio + timedelta(minutes=30)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(turno, nuevo_inicio, nuevo_fin),
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.CONFIRMADO

    def test_medico_no_puede_reprogramar_ajeno(self):
        user = User.objects.create_user(
            username='te_rep_med_no', email='te_rep_med_no@test.com', password='x', rol='medico',
        )
        self.medico_b.user = user
        self.medico_b.save()
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 3)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno,
                turno.fecha_hora_inicio + timedelta(days=1),
                turno.fecha_hora_fin + timedelta(days=1),
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_medico_no_puede_cambiar_medico_id(self):
        user = User.objects.create_user(
            username='te_rep_med_sw', email='te_rep_med_sw@test.com', password='x', rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 4)
        nuevo_inicio = turno.fecha_hora_inicio + timedelta(days=3)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno, nuevo_inicio, nuevo_inicio + timedelta(minutes=30),
                medico_id=self.medico_b.id,
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_paciente_propio_puede_reprogramar(self):
        user = User.objects.create_user(
            username='te_rep_pac', email='te_rep_pac@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 5)
        nuevo_inicio = turno.fecha_hora_inicio + timedelta(days=4)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(turno, nuevo_inicio, nuevo_inicio + timedelta(minutes=30)),
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_paciente_no_puede_reprogramar_ajeno(self):
        otro = Paciente.objects.create(dni='TE-REP-OT', nombre='Otro', apellido='Pac')
        user = User.objects.create_user(
            username='te_rep_pac_no', email='te_rep_pac_no@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        base = timezone.now() + timedelta(hours=210)
        turno = Turno.objects.create(
            paciente=otro,
            medico=self.medico_a,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.RESERVADO,
        )
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno,
                base + timedelta(days=1),
                base + timedelta(days=1, minutes=30),
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_enfermeria_no_puede_reprogramar(self):
        enf = User.objects.create_user(
            username='te_rep_enf', email='te_rep_enf@test.com', password='x', rol='enfermeria',
        )
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 6)
        self.client.force_authenticate(user=enf)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno,
                turno.fecha_hora_inicio + timedelta(days=1),
                turno.fecha_hora_fin + timedelta(days=1),
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_reprogramar(self):
        lab = User.objects.create_user(
            username='te_rep_lab', email='te_rep_lab@test.com', password='x', rol='laboratorio',
        )
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 7)
        self.client.force_authenticate(user=lab)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno,
                turno.fecha_hora_inicio + timedelta(days=1),
                turno.fecha_hora_fin + timedelta(days=1),
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_reprogramar_cancelado_devuelve_400(self):
        admin = User.objects.create_user(
            username='te_rep_can', email='te_rep_can@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.CANCELADO, 8)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno,
                turno.fecha_hora_inicio + timedelta(days=1),
                turno.fecha_hora_fin + timedelta(days=1),
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_reprogramar_realizado_devuelve_400(self):
        admin = User.objects.create_user(
            username='te_rep_rea', email='te_rep_rea@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.REALIZADO, 9)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            self._payload_reprog(
                turno,
                turno.fecha_hora_inicio + timedelta(days=1),
                turno.fecha_hora_fin + timedelta(days=1),
            ),
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_reprogramar_fin_menor_igual_inicio_400(self):
        admin = User.objects.create_user(
            username='te_rep_fin', email='te_rep_fin@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 10)
        inicio = turno.fecha_hora_inicio + timedelta(days=1)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/reprogramar/',
            {
                'fecha_hora_inicio': inicio.isoformat(),
                'fecha_hora_fin': inicio.isoformat(),
                'motivo': 'Fin inválido',
            },
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_reprogramar_solapamiento_400(self):
        admin = User.objects.create_user(
            username='te_rep_sol', email='te_rep_sol@test.com', password='x',
            rol='admin', is_staff=True,
        )
        t1 = self._turno(self.medico_a, Turno.Estado.RESERVADO, 11)
        t2 = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 12)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{t2.id}/reprogramar/',
            self._payload_reprog(t2, t1.fecha_hora_inicio, t1.fecha_hora_fin),
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_reprogramar_auditoria_metadata(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_rep_aud', email='te_rep_aud@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 13)
        nuevo_inicio = turno.fecha_hora_inicio + timedelta(days=5)
        nuevo_fin = nuevo_inicio + timedelta(minutes=30)
        self.client.force_authenticate(user=admin)
        with capture_on_commit_callbacks(execute=True):
            self.client.post(
                f'/api/turnos/{turno.id}/reprogramar/',
                self._payload_reprog(
                    turno, nuevo_inicio, nuevo_fin,
                    recurso_id=self.recurso_b.id,
                    motivo='Cambio de sala',
                ),
                format='json',
            )
        ev = AuditEvent.objects.filter(
            entity_type='turnos.Turno',
            entity_id=str(turno.id),
            action='UPDATE',
        ).order_by('-id').first()
        assert ev is not None
        assert ev.metadata.get('accion') == 'reprogramar_turno'
        assert ev.metadata.get('estado_anterior') == Turno.Estado.RESERVADO
        assert ev.metadata.get('estado_nuevo') == Turno.Estado.RESERVADO
        assert 'fecha_hora_inicio_nueva' in ev.metadata
        assert ev.metadata.get('motivo') == 'Cambio de sala'
        assert ev.metadata.get('view') == 'TurnoViewSet.reprogramar'


@pytest.mark.django_db
class TestMarcarRealizadoTurno(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología Real')
        cls.paciente = Paciente.objects.create(
            dni='TE-REA-P', nombre='Pac', apellido='Rea',
        )
        cls.medico_a = Medico.objects.create(
            nombre='Dr', apellido='ReaA', matricula='TE-REA-A', especialidad=cls.especialidad,
        )
        cls.medico_b = Medico.objects.create(
            nombre='Dr', apellido='ReaB', matricula='TE-REA-B', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('rea')

    def _turno(self, medico, estado, suffix: int) -> Turno:
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=220 + suffix)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=estado,
        )

    def test_secretaria_puede_marcar_realizado_desde_reservado(self):
        sec = User.objects.create_user(
            username='te_rea_sec', email='te_rea_sec@test.com', password='x', rol='secretaria',
        )
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 1)
        self.client.force_authenticate(user=sec)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.REALIZADO

    def test_medico_propio_confirmado_a_realizado(self):
        user = User.objects.create_user(
            username='te_rea_med', email='te_rea_med@test.com', password='x', rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 2)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.REALIZADO

    def test_medico_ajeno_no_puede_marcar_realizado(self):
        user = User.objects.create_user(
            username='te_rea_med_no', email='te_rea_med_no@test.com', password='x', rol='medico',
        )
        self.medico_b.user = user
        self.medico_b.save()
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 3)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_medico_reservado_no_puede_marcar_realizado(self):
        user = User.objects.create_user(
            username='te_rea_med_res', email='te_rea_med_res@test.com', password='x', rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 4)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_no_puede_marcar_realizado(self):
        user = User.objects.create_user(
            username='te_rea_pac', email='te_rea_pac@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 5)
        self.client.force_authenticate(user=user)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_enfermeria_no_puede_marcar_realizado(self):
        enf = User.objects.create_user(
            username='te_rea_enf', email='te_rea_enf@test.com', password='x', rol='enfermeria',
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 6)
        self.client.force_authenticate(user=enf)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_marcar_realizado(self):
        lab = User.objects.create_user(
            username='te_rea_lab', email='te_rea_lab@test.com', password='x', rol='laboratorio',
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 7)
        self.client.force_authenticate(user=lab)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_cancelado_a_realizado_400(self):
        admin = User.objects.create_user(
            username='te_rea_can', email='te_rea_can@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.CANCELADO, 8)
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_disponible_a_realizado_400(self):
        admin = User.objects.create_user(
            username='te_rea_disp', email='te_rea_disp@test.com', password='x',
            rol='admin', is_staff=True,
        )
        base = timezone.now() + timedelta(hours=230)
        turno = Turno.objects.create(
            medico=self.medico_a,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=Turno.Estado.DISPONIBLE,
        )
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_realizado_idempotente_sin_auditoria_duplicada(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_rea_idem', email='te_rea_idem@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.REALIZADO, 9)
        self.client.force_authenticate(user=admin)
        n_before = _audit_update_count(turno.id)
        with capture_on_commit_callbacks(execute=True):
            r = self.client.post(f'/api/turnos/{turno.id}/marcar-realizado/', {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert r.data['applied'] is False
        assert _audit_update_count(turno.id) == n_before

    def test_marcar_realizado_auditoria_metadata(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_rea_aud', email='te_rea_aud@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 10)
        self.client.force_authenticate(user=admin)
        with capture_on_commit_callbacks(execute=True):
            self.client.post(
                f'/api/turnos/{turno.id}/marcar-realizado/',
                {'motivo': 'Atención realizada'},
                format='json',
            )
        ev = AuditEvent.objects.filter(
            entity_type='turnos.Turno',
            entity_id=str(turno.id),
            action='UPDATE',
        ).order_by('-id').first()
        assert ev.metadata.get('accion') == 'marcar_realizado_turno'
        assert ev.metadata.get('estado_anterior') == Turno.Estado.CONFIRMADO
        assert ev.metadata.get('estado_nuevo') == Turno.Estado.REALIZADO
        assert ev.metadata.get('motivo') == 'Atención realizada'
        assert ev.metadata.get('view') == 'TurnoViewSet.marcar_realizado'


@pytest.mark.django_db
class TestMarcarNoAsistioTurno(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especialidad = _esp('Cardiología NoAsis')
        cls.paciente = Paciente.objects.create(
            dni='TE-NA-P', nombre='Pac', apellido='Na',
        )
        cls.medico_a = Medico.objects.create(
            nombre='Dr', apellido='NaA', matricula='TE-NA-A', especialidad=cls.especialidad,
        )
        cls.medico_b = Medico.objects.create(
            nombre='Dr', apellido='NaB', matricula='TE-NA-B', especialidad=cls.especialidad,
        )
        cls.recurso = _recurso('na')

    def _turno(self, medico, estado, suffix: int) -> Turno:
        base = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=240 + suffix)
        return Turno.objects.create(
            paciente=self.paciente,
            medico=medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=30),
            estado=estado,
        )

    def test_secretaria_puede_marcar_no_asistio(self):
        sec = User.objects.create_user(
            username='te_na_sec', email='te_na_sec@test.com', password='x', rol='secretaria',
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 1)
        self.client.force_authenticate(user=sec)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'No asistió'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert turno.estado == Turno.Estado.CANCELADO

    def test_medico_propio_puede_marcar_no_asistio(self):
        user = User.objects.create_user(
            username='te_na_med', email='te_na_med@test.com', password='x', rol='medico',
        )
        self.medico_a.user = user
        self.medico_a.save()
        turno = self._turno(self.medico_a, Turno.Estado.RESERVADO, 2)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'Paciente no vino'},
            format='json',
        )
        assert r.status_code == status.HTTP_200_OK

    def test_paciente_no_puede_marcar_no_asistio(self):
        user = User.objects.create_user(
            username='te_na_pac', email='te_na_pac@test.com', password='x', rol='paciente',
        )
        self.paciente.user = user
        self.paciente.save()
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 3)
        self.client.force_authenticate(user=user)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'X'},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_enfermeria_no_puede_marcar_no_asistio(self):
        enf = User.objects.create_user(
            username='te_na_enf', email='te_na_enf@test.com', password='x', rol='enfermeria',
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 4)
        self.client.force_authenticate(user=enf)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'X'},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_puede_marcar_no_asistio(self):
        lab = User.objects.create_user(
            username='te_na_lab', email='te_na_lab@test.com', password='x', rol='laboratorio',
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 5)
        self.client.force_authenticate(user=lab)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'X'},
            format='json',
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_motivo_obligatorio(self):
        admin = User.objects.create_user(
            username='te_na_mot', email='te_na_mot@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 6)
        self.client.force_authenticate(user=admin)
        r = self.client.post(f'/api/turnos/{turno.id}/marcar-no-asistio/', {}, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_realizado_devuelve_400(self):
        admin = User.objects.create_user(
            username='te_na_rea', email='te_na_rea@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.REALIZADO, 7)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'Tarde'},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancelado_devuelve_400(self):
        admin = User.objects.create_user(
            username='te_na_can', email='te_na_can@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.CANCELADO, 8)
        self.client.force_authenticate(user=admin)
        r = self.client.post(
            f'/api/turnos/{turno.id}/marcar-no-asistio/',
            {'motivo': 'Reintento'},
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_marcar_no_asistio_auditoria_accion(self):
        from auditoria.tests.compat import capture_on_commit_callbacks

        admin = User.objects.create_user(
            username='te_na_aud', email='te_na_aud@test.com', password='x',
            rol='admin', is_staff=True,
        )
        turno = self._turno(self.medico_a, Turno.Estado.CONFIRMADO, 9)
        self.client.force_authenticate(user=admin)
        with capture_on_commit_callbacks(execute=True):
            self.client.post(
                f'/api/turnos/{turno.id}/marcar-no-asistio/',
                {'motivo': 'El paciente no asistió'},
                format='json',
            )
        ev = AuditEvent.objects.filter(
            entity_type='turnos.Turno',
            entity_id=str(turno.id),
            action='UPDATE',
        ).order_by('-id').first()
        assert ev.metadata.get('accion') == 'marcar_no_asistio'
        assert ev.metadata.get('estado_nuevo') == Turno.Estado.CANCELADO
        assert ev.metadata.get('motivo') == 'El paciente no asistió'
        assert ev.metadata.get('view') == 'TurnoViewSet.marcar_no_asistio'
