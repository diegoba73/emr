"""Aviso de asistencia ~48 hs antes + adelanto a viernes si cae finde."""

from datetime import datetime, time, timedelta
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from medicos.models import Medico
from movil.models import DispositivoPush, RecordatorioTurno, SesionMovil
from movil.recordatorios import (
    momento_aviso_asistencia_48h,
    preparar_recordatorios_asistencia,
)
from pacientes.models import Paciente
from turnos.models import Turno

pytestmark = pytest.mark.django_db


def _aware(d, h=10, m=0):
    return timezone.make_aware(datetime.combine(d, time(h, m)))


def test_momento_aviso_48h_dia_habil():
    # Miércoles 10:00 → 48 hs antes = lunes 10:00 (sin corrimiento).
    miercoles = timezone.localdate()
    while miercoles.weekday() != 2:
        miercoles += timedelta(days=1)
    inicio = _aware(miercoles, 10)
    aviso = momento_aviso_asistencia_48h(inicio)
    assert timezone.localtime(aviso).weekday() == 0  # lunes
    assert aviso == inicio - timedelta(hours=48)


def test_momento_aviso_lunes_cae_sabado_adelanta_viernes():
    # Lunes 10:00 → 48 hs = sábado 10:00 → viernes 10:00.
    lunes = timezone.localdate()
    while lunes.weekday() != 0:
        lunes += timedelta(days=1)
    inicio = _aware(lunes, 10)
    aviso = momento_aviso_asistencia_48h(inicio)
    local = timezone.localtime(aviso)
    assert local.weekday() == 4  # viernes
    assert local.hour == 10
    assert aviso == inicio - timedelta(hours=48) - timedelta(days=1)


def test_momento_aviso_domingo_nominal_adelanta_viernes():
    # Martes 10:00 → 48 hs = domingo 10:00 → viernes 10:00.
    martes = timezone.localdate()
    while martes.weekday() != 1:
        martes += timedelta(days=1)
    inicio = _aware(martes, 10)
    aviso = momento_aviso_asistencia_48h(inicio)
    assert timezone.localtime(aviso).weekday() == 4
    assert aviso == inicio - timedelta(hours=48) - timedelta(days=2)


def _turno_confirmado_con_push(*, inicio):
    cache.clear()
    U = get_user_model()
    u = U.objects.create_user(username='pac48h', password='x', rol='paciente')
    p = Paciente.objects.create(user=u, nombre='P', apellido='48', dni='DNI-48')
    m = Medico.objects.create(nombre='M', apellido='48', matricula='M-48')
    t = Turno.objects.create(
        paciente=p,
        medico=m,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=inicio + timedelta(minutes=20),
        estado=Turno.Estado.CONFIRMADO,
    )
    c = APIClient()
    r = c.post(
        '/api/movil/login/',
        {'username': u.username, 'password': 'x'},
        format='json',
    )
    assert r.status_code == 200, r.data
    s = SesionMovil.objects.get(user=u)
    DispositivoPush.objects.create(sesion=s, token='ExpoPushToken[48h]', plataforma='android')
    return t


def test_prepara_asistencia_al_llegar_a_ventana_48h():
    inicio = timezone.now() + timedelta(hours=47)
    t = _turno_confirmado_con_push(inicio=inicio)
    assert preparar_recordatorios_asistencia(now=timezone.now()) == 1
    assert RecordatorioTurno.objects.filter(turno=t, tipo='ASISTENCIA').exists()


def test_no_prepara_antes_de_ventana_48h():
    inicio = timezone.now() + timedelta(hours=60)
    _turno_confirmado_con_push(inicio=inicio)
    # 60 hs > 48 hs y cae en día hábil típico → aún no.
    assert preparar_recordatorios_asistencia(now=timezone.now()) == 0


def test_lunes_prepara_desde_viernes_no_sabado():
    lunes = timezone.localdate() + timedelta(days=1)
    while lunes.weekday() != 0:
        lunes += timedelta(days=1)
    inicio = _aware(lunes, 10)
    t = _turno_confirmado_con_push(inicio=inicio)
    aviso = momento_aviso_asistencia_48h(inicio)
    assert timezone.localtime(aviso).weekday() == 4

    # Jueves (antes del viernes de aviso): no prepara.
    jueves = aviso - timedelta(days=1)
    assert preparar_recordatorios_asistencia(now=jueves) == 0

    # Viernes a la hora del aviso: sí prepara.
    assert preparar_recordatorios_asistencia(now=aviso) == 1
    assert RecordatorioTurno.objects.filter(turno=t, tipo='ASISTENCIA').count() == 1

    # Idempotente.
    assert preparar_recordatorios_asistencia(now=aviso + timedelta(hours=1)) == 0


def test_envio_asistencia_menciona_48_horas(settings):
    settings.MOBILE_PUSH_ENABLED = True
    inicio = timezone.now() + timedelta(hours=40)
    t = _turno_confirmado_con_push(inicio=inicio)
    assert preparar_recordatorios_asistencia() == 1
    from movil.recordatorios import enviar_pendientes

    with patch(
        'movil.recordatorios.requests.post',
        return_value=Mock(json=lambda: {'data': {'status': 'ok', 'id': 't-48'}}),
    ) as send:
        assert enviar_pendientes() == 1
        body = send.call_args.kwargs['json']['body']
        assert '48' in body
        assert send.call_args.kwargs['json']['data']['turno_id'] == t.pk


def test_aviso_estoy_en_sala_una_hora_antes(settings):
    from movil.recordatorios import preparar_recordatorios_estoy_en_sala, enviar_pendientes

    settings.MOBILE_PUSH_ENABLED = True
    # Fuera de ventana (2 h) → no prepara.
    t = _turno_confirmado_con_push(inicio=timezone.now() + timedelta(hours=2))
    assert preparar_recordatorios_estoy_en_sala() == 0

    # Dentro de ventana (30 min) → sí.
    t.fecha_hora_inicio = timezone.now() + timedelta(minutes=30)
    t.fecha_hora_fin = t.fecha_hora_inicio + timedelta(minutes=20)
    t.save(update_fields=['fecha_hora_inicio', 'fecha_hora_fin'])
    assert preparar_recordatorios_estoy_en_sala() == 1
    assert RecordatorioTurno.objects.filter(turno=t, tipo='ESTOY_EN_SALA').exists()
    assert preparar_recordatorios_estoy_en_sala() == 0  # idempotente

    with patch(
        'movil.recordatorios.requests.post',
        return_value=Mock(json=lambda: {'data': {'status': 'ok', 'id': 't-sala'}}),
    ) as send:
        assert enviar_pendientes() == 1
        body = send.call_args.kwargs['json']['body']
        assert '1 hora' in body
        assert 'sala' in body.lower()
        assert send.call_args.kwargs['json']['data']['tipo'] == 'estoy_en_sala'
        assert send.call_args.kwargs['json']['data']['turno_id'] == t.pk
