"""Políticas reserva móvil: cancel/reprog paciente, cobertura, flag pago."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from medicos.models import DisponibilidadMedico, Medico
from pacientes.models import Paciente
from pacientes.tests.os_helpers import os_ref
from turnos.models import Recurso, Turno

pytestmark = pytest.mark.django_db


def _client_paciente(*, dni='POL-1', obra='PARTICULAR', afiliado='', plan=''):
    cache.clear()
    U = get_user_model()
    u = U.objects.create_user(username=dni, password='test-password', rol='paciente')
    p = Paciente.objects.create(
        user=u,
        nombre='Pol',
        apellido='Test',
        dni=dni,
        obra_social=os_ref(obra),
        numero_afiliado=afiliado or None,
        plan_obra_social=plan or '',
    )
    d = U.objects.create_user(username=f'doc-{dni}', password='test-password', rol='medico')
    m = Medico.objects.create(user=d, nombre='Doc', apellido=dni, matricula=f'M-{dni}')
    c = APIClient()
    r = c.post(
        '/api/movil/login/',
        {'username': u.username, 'password': 'test-password'},
        format='json',
    )
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['token'])
    return c, u, p, m


def _horario(medico, day, cons=None):
    if cons is None:
        cons = Recurso.objects.create(
            nombre=f'Cons {medico.pk}',
            ubicacion='CEHTA',
            tipo_recurso='CONSULTORIO',
            activo=True,
        )
    return DisponibilidadMedico.objects.create(
        medico=medico,
        dia_semana=day.weekday(),
        hora_inicio=time(9),
        hora_fin=time(13),
        tipo='CONSULTA',
        recurso=cons,
        activo=True,
    ), cons


def test_cancel_paciente_403_salvo_rechazo_reprogramacion():
    c, u, p, m = _client_paciente()
    start = timezone.now() + timedelta(days=5)
    t = Turno.objects.create(
        paciente=p,
        medico=m,
        fecha_hora_inicio=start,
        fecha_hora_fin=start + timedelta(minutes=20),
        estado=Turno.Estado.CONFIRMADO,
    )
    assert c.post(f'/api/movil/turnos/{t.pk}/cancelar/', {'motivo': 'No voy'}, format='json').status_code == 403

    t.requiere_aceptacion_paciente = True
    t.estado = Turno.Estado.RESERVADO
    t.save(update_fields=['requiere_aceptacion_paciente', 'estado', 'updated_at'])
    r = c.post(
        f'/api/movil/turnos/{t.pk}/cancelar/',
        {'motivo': 'Rechazo horario propuesto'},
        format='json',
    )
    assert r.status_code == 200, r.data
    t.refresh_from_db()
    assert t.estado == Turno.Estado.CANCELADO


def test_reprogram_paciente_menos_48h_bloqueado():
    c, u, p, m = _client_paciente(dni='POL-48')
    day = timezone.localdate() + timedelta(days=1)
    start = timezone.make_aware(datetime.combine(day, time(10)))
    # Asegurar < 48 h
    if start - timezone.now() >= timedelta(hours=48):
        start = timezone.now() + timedelta(hours=30)
        day = timezone.localdate(start)
    cons = Recurso.objects.create(
        nombre='Cons 48', ubicacion='CEHTA', tipo_recurso='CONSULTORIO', activo=True
    )
    h, _ = _horario(m, day, cons)
    t = Turno.objects.create(
        paciente=p,
        medico=m,
        recurso=cons,
        fecha_hora_inicio=start,
        fecha_hora_fin=start + timedelta(minutes=20),
        estado=Turno.Estado.RESERVADO,
    )
    r = c.post(
        f'/api/movil/turnos/{t.pk}/reprogramar-horario/',
        {
            'horario_id': h.pk,
            'inicio': (start + timedelta(minutes=20)).isoformat(),
            'motivo': 'Cambio',
        },
        format='json',
    )
    assert r.status_code in (400, 403)


def test_reserva_os_sin_plan_400():
    c, u, p, m = _client_paciente(dni='POL-OS', obra='OSDE', afiliado='', plan='')
    day = timezone.localdate() + timedelta(days=7)
    start = timezone.make_aware(datetime.combine(day, time(9)))
    h, _ = _horario(m, day)
    r = c.post(
        '/api/movil/turnos/reservar-horario/',
        {'horario_id': h.pk, 'inicio': start.isoformat()},
        format='json',
    )
    assert r.status_code == 400
    assert 'cobertura' in str(r.data).lower() or 'afiliado' in str(r.data).lower() or 'plan' in str(r.data).lower()


def test_reserva_os_completa_ok_y_pago_flag_off():
    c, u, p, m = _client_paciente(
        dni='POL-OK', obra='OSDE', afiliado='12345', plan='210'
    )
    day = timezone.localdate() + timedelta(days=7)
    start = timezone.make_aware(datetime.combine(day, time(9)))
    h, _ = _horario(m, day)
    with patch('django.conf.settings.MOBILE_PAGO_RESERVA_ENABLED', False):
        r = c.post(
            '/api/movil/turnos/reservar-horario/',
            {'horario_id': h.pk, 'inicio': start.isoformat()},
            format='json',
        )
    assert r.status_code == 201, r.data


def test_pago_flag_on_bloquea_hasta_integracion(settings):
    settings.MOBILE_PAGO_RESERVA_ENABLED = True
    c, u, p, m = _client_paciente(dni='POL-PAY')
    day = timezone.localdate() + timedelta(days=7)
    start = timezone.make_aware(datetime.combine(day, time(9)))
    h, _ = _horario(m, day)
    r = c.post(
        '/api/movil/turnos/reservar-horario/',
        {'horario_id': h.pk, 'inicio': start.isoformat()},
        format='json',
    )
    assert r.status_code == 400
    assert 'cobro' in str(r.data).lower() or 'pago' in str(r.data).lower()
