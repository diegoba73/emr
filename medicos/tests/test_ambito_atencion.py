"""Tests de ámbito de atención del médico."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from medicos.ambito import contextos_lab_permitidos, user_medico_es_solo_ambulatorio
from medicos.models import Medico

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_contextos_lab_solo_ambulatorio():
    user = User.objects.create_user(username='m1', password='x', rol='medico')
    medico = Medico.objects.create(
        user=user,
        nombre='A',
        apellido='B',
        matricula='M-AMB',
        ambito_atencion=Medico.AMBITO_AMBULATORIO,
    )
    assert contextos_lab_permitidos(medico) == ('AMBULATORIO',)
    assert user_medico_es_solo_ambulatorio(user) is True


def test_medico_ambulatorio_sin_acceso_internacion_api():
    user = User.objects.create_user(username='m2', password='x', rol='medico')
    Medico.objects.create(
        user=user,
        nombre='A',
        apellido='B',
        matricula='M-AMB2',
        ambito_atencion=Medico.AMBITO_AMBULATORIO,
    )
    c = APIClient()
    c.force_authenticate(user=user)
    r = c.get('/api/internacion/internaciones/')
    assert r.status_code == 403


def test_medico_ambulatorio_no_inicia_guardia():
    user = User.objects.create_user(username='m3', password='x', rol='medico')
    Medico.objects.create(
        user=user,
        nombre='A',
        apellido='B',
        matricula='M-AMB3',
        ambito_atencion=Medico.AMBITO_AMBULATORIO,
    )
    c = APIClient()
    c.force_authenticate(user=user)
    r = c.post(
        '/api/atenciones/iniciar-guardia/',
        {'paciente_id': 1, 'medico_id': user.medico.id},
        format='json',
    )
    assert r.status_code == 403
