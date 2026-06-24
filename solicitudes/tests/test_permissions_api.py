"""
Tests PERM-01 / INT-01 — permisos y auditoría de solicitudes genéricas EMR.
"""
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from auditoria.tests.compat import capture_on_commit_callbacks
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from solicitudes.models import Solicitud

User = get_user_model()


def _payload(paciente_id, **extra):
    data = {
        'paciente': paciente_id,
        'tipo_solicitud': 'EXAMEN_LABORATORIO',
        'descripcion': 'Hemograma confidencial',
        'observaciones': 'Nota clínica sensible',
        'prioridad': 'NORMAL',
    }
    data.update(extra)
    return data


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user_admin(db):
    return User.objects.create_user(
        username='adm_sol', password='x', rol='admin', is_staff=True
    )


@pytest.fixture
def user_secretaria(db):
    return User.objects.create_user(
        username='sec_sol', password='x', rol='secretaria', is_staff=True
    )


@pytest.fixture
def user_lab(db):
    return User.objects.create_user(
        username='lab_sol', password='x', rol='laboratorio', is_staff=True
    )


@pytest.fixture
def user_enfermeria(db):
    return User.objects.create_user(
        username='enf_sol', password='x', rol='enfermeria', is_staff=True
    )


@pytest.fixture
def user_sin_rol(db):
    return User.objects.create_user(username='norol_sol', password='x', rol='')


@pytest.fixture
def user_paciente(db, paciente_a):
    user = User.objects.create_user(username='pac_sol', password='x', rol='paciente')
    paciente_a.user = user
    paciente_a.save(update_fields=['user'])
    return user


@pytest.fixture
def user_paciente_b(db, paciente_b):
    user = User.objects.create_user(username='pac_b_sol', password='x', rol='paciente')
    paciente_b.user = user
    paciente_b.save(update_fields=['user'])
    return user


@pytest.fixture
def solicitud_vinculada(db, paciente_a, medico_profile):
    return Solicitud.objects.create(
        paciente=paciente_a,
        medico_solicitante=medico_profile,
        tipo_solicitud='EXAMEN_LABORATORIO',
        descripcion='Solicitud vinculada',
        creado_por=medico_profile.user,
        modificado_por=medico_profile.user,
    )


@pytest.fixture
def solicitud_ajena(db, paciente_b, medico_otro):
    return Solicitud.objects.create(
        paciente=paciente_b,
        medico_solicitante=medico_otro,
        tipo_solicitud='EXAMEN_LABORATORIO',
        descripcion='Solicitud ajena',
        creado_por=medico_otro.user,
        modificado_por=medico_otro.user,
    )


@pytest.mark.django_db
class TestSolicitudPermisosAcceso:
    def test_anonimo_no_accede(self, api):
        assert api.get('/api/solicitudes/').status_code in (401, 403)

    def test_usuario_sin_rol_no_lista(self, api, user_sin_rol):
        api.force_authenticate(user=user_sin_rol)
        assert api.get('/api/solicitudes/').status_code == status.HTTP_403_FORBIDDEN

    def test_laboratorio_no_opera(self, api, user_lab):
        api.force_authenticate(user=user_lab)
        assert api.get('/api/solicitudes/').status_code == status.HTTP_403_FORBIDDEN

    def test_enfermeria_no_opera(self, api, user_enfermeria):
        api.force_authenticate(user=user_enfermeria)
        assert api.get('/api/solicitudes/').status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSolicitudPermisosCreate:
    def test_usuario_sin_rol_no_crea(self, api, user_sin_rol, paciente_a):
        api.force_authenticate(user=user_sin_rol)
        r = api.post('/api/solicitudes/', _payload(paciente_a.pk), format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_no_crea(self, api, user_paciente, paciente_a):
        api.force_authenticate(user=user_paciente)
        r = api.post('/api/solicitudes/', _payload(paciente_a.pk), format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_no_crea_para_otro(self, api, user_paciente, paciente_b):
        api.force_authenticate(user=user_paciente)
        r = api.post('/api/solicitudes/', _payload(paciente_b.pk), format='json')
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_medico_crea_con_vinculo(self, api, medico_profile, paciente_a):
        api.force_authenticate(user=medico_profile.user)
        r = api.post('/api/solicitudes/', _payload(paciente_a.pk), format='json')
        assert r.status_code in (200, 201)
        sol = Solicitud.objects.filter(paciente=paciente_a).latest('id')
        assert sol.medico_solicitante_id == medico_profile.pk

    @patch('integracion_lims.lims_service.enviar_solicitud_a_lims')
    def test_create_medico_con_lims_paneles_no_envia_lims(
        self, mock_lims, api, medico_profile, paciente_a
    ):
        api.force_authenticate(user=medico_profile.user)
        r = api.post(
            '/api/solicitudes/',
            _payload(paciente_a.pk, lims_paneles=['P1'], lims_tipos_examen=['GLU']),
            format='json',
        )
        assert r.status_code in (200, 201)
        mock_lims.assert_not_called()


@pytest.mark.django_db
class TestSolicitudPermisosMutaciones:
    def test_paciente_no_cambia_estado(self, api, user_paciente, solicitud_vinculada):
        api.force_authenticate(user=user_paciente)
        sol = solicitud_vinculada
        sol.paciente = user_paciente.paciente
        sol.save(update_fields=['paciente'])
        r = api.patch(
            f'/api/solicitudes/{sol.pk}/cambiar_estado/',
            {'estado': 'EN_PROCESO'},
            format='json',
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_paciente_no_cancela(self, api, user_paciente, solicitud_vinculada):
        api.force_authenticate(user=user_paciente)
        sol = solicitud_vinculada
        sol.paciente = user_paciente.paciente
        sol.save(update_fields=['paciente'])
        assert api.post(f'/api/solicitudes/{sol.pk}/cancelar/').status_code == 403

    def test_paciente_no_reabre(self, api, user_paciente, solicitud_vinculada):
        api.force_authenticate(user=user_paciente)
        sol = solicitud_vinculada
        sol.paciente = user_paciente.paciente
        sol.estado = 'CANCELADA'
        sol.save(update_fields=['paciente', 'estado'])
        assert api.post(f'/api/solicitudes/{sol.pk}/reabrir/').status_code == 403

    @patch('integracion_lims.lims_service.enviar_solicitud_a_lims')
    def test_paciente_no_envia_lims(self, mock_lims, api, user_paciente, solicitud_vinculada):
        api.force_authenticate(user=user_paciente)
        sol = solicitud_vinculada
        sol.paciente = user_paciente.paciente
        sol.save(update_fields=['paciente'])
        r = api.post(f'/api/solicitudes/{sol.pk}/enviar_lims/', {}, format='json')
        assert r.status_code == 403
        mock_lims.assert_not_called()

    @patch('integracion_lims.lims_service.enviar_solicitud_a_lims')
    def test_secretaria_no_envia_lims(self, mock_lims, api, user_secretaria, solicitud_vinculada):
        api.force_authenticate(user=user_secretaria)
        r = api.post(
            f'/api/solicitudes/{solicitud_vinculada.pk}/enviar_lims/',
            {'paneles': ['P1']},
            format='json',
        )
        assert r.status_code == 403
        mock_lims.assert_not_called()

    def test_secretaria_no_sincroniza_lims(self, api, user_secretaria, solicitud_vinculada):
        api.force_authenticate(user=user_secretaria)
        assert (
            api.post(f'/api/solicitudes/{solicitud_vinculada.pk}/sincronizar_lims/').status_code
            == 403
        )

    def test_medico_no_opera_solicitud_no_vinculada(self, api, medico_profile, solicitud_ajena):
        api.force_authenticate(user=medico_profile.user)
        assert api.get(f'/api/solicitudes/{solicitud_ajena.pk}/').status_code == 404

    def test_medico_no_cambia_estado(self, api, medico_profile, solicitud_vinculada):
        api.force_authenticate(user=medico_profile.user)
        r = api.patch(
            f'/api/solicitudes/{solicitud_vinculada.pk}/cambiar_estado/',
            {'estado': 'EN_PROCESO'},
            format='json',
        )
        assert r.status_code == 403

    def test_medico_puede_leer_vinculada(self, api, medico_profile, solicitud_vinculada):
        api.force_authenticate(user=medico_profile.user)
        assert api.get(f'/api/solicitudes/{solicitud_vinculada.pk}/').status_code == 200

    def test_estado_no_cambia_por_patch_estandar(self, api, user_admin, solicitud_vinculada):
        api.force_authenticate(user=user_admin)
        r = api.patch(
            f'/api/solicitudes/{solicitud_vinculada.pk}/',
            {'estado': 'EN_PROCESO'},
            format='json',
        )
        assert r.status_code == 200
        solicitud_vinculada.refresh_from_db()
        assert solicitud_vinculada.estado == 'PENDIENTE'

    def test_destroy_bloqueado_para_medico(self, api, medico_profile, solicitud_vinculada):
        api.force_authenticate(user=medico_profile.user)
        assert api.delete(f'/api/solicitudes/{solicitud_vinculada.pk}/').status_code == 403


@pytest.mark.django_db
class TestSolicitudLimsYAuditoria:
    @patch('integracion_lims.lims_service.enviar_solicitud_a_lims', return_value={'id': 'LIMS-99'})
    def test_admin_enviar_lims_auditado_sin_phi(self, mock_lims, api, user_admin, solicitud_vinculada):
        api.force_authenticate(user=user_admin)
        with capture_on_commit_callbacks(execute=True):
            r = api.post(
                f'/api/solicitudes/{solicitud_vinculada.pk}/enviar_lims/',
                {'paneles': ['P1'], 'tipos_examen': ['GLU']},
                format='json',
            )
        assert r.status_code == 200
        ev = (
            AuditEvent.objects.filter(
                entity_type=Solicitud._meta.label,
                entity_id=str(solicitud_vinculada.pk),
                action='UPDATE',
                module='solicitudes',
            )
            .order_by('-id')
            .first()
        )
        assert ev is not None
        meta = ev.metadata or {}
        meta_raw = json.dumps(meta, ensure_ascii=False, default=str)
        assert meta.get('accion') == 'solicitud_lims_enviar'
        assert meta.get('destino') == 'lims_externo'
        assert meta.get('success') is True
        assert 'Hemograma' not in meta_raw
        assert 'confidencial' not in meta_raw
        assert 'paciente_nombre' not in meta

    @patch.object(Solicitud, '_enviar_a_lims')
    def test_admin_sincronizar_lims_auditado_sin_phi(
        self, mock_enviar, api, user_admin, solicitud_vinculada
    ):
        def _sync():
            solicitud_vinculada.sincronizado_lims = True
            solicitud_vinculada.lims_id = 'LIMS-SYNC'
            solicitud_vinculada.save(update_fields=['sincronizado_lims', 'lims_id'])

        mock_enviar.side_effect = _sync
        api.force_authenticate(user=user_admin)
        with capture_on_commit_callbacks(execute=True):
            r = api.post(f'/api/solicitudes/{solicitud_vinculada.pk}/sincronizar_lims/')
        assert r.status_code == 200
        ev = (
            AuditEvent.objects.filter(
                entity_type=Solicitud._meta.label,
                entity_id=str(solicitud_vinculada.pk),
                action='UPDATE',
            )
            .order_by('-id')
            .first()
        )
        assert ev is not None
        assert ev.metadata.get('accion') == 'solicitud_lims_sincronizar'
        assert 'payload' not in (ev.metadata or {})

    def test_admin_destroy_auditado(self, api, user_admin, paciente_a, medico_profile):
        sol = Solicitud.objects.create(
            paciente=paciente_a,
            medico_solicitante=medico_profile,
            tipo_solicitud='OTRO',
            descripcion='Borrar',
        )
        api.force_authenticate(user=user_admin)
        with capture_on_commit_callbacks(execute=True):
            r = api.delete(f'/api/solicitudes/{sol.pk}/')
        assert r.status_code == 204
        ev = AuditEvent.objects.filter(
            entity_type=Solicitud._meta.label,
            entity_id=str(sol.pk),
            action='DELETE',
        ).first()
        assert ev is not None
        assert ev.metadata.get('accion') == 'solicitud_destroy'
        assert 'Ana' not in (ev.entity_repr or '')
