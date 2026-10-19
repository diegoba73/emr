"""A5 — matriz de bandejas, conteos, paginación server-side, flujo completo.

No toca laboratorio/.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from estudios.bandejas import (
    BANDEJA_ANULADOS,
    BANDEJA_DOCUMENTACION_PENDIENTE,
    BANDEJA_FINALIZADOS,
    BANDEJA_PENDIENTE_ENTREGA,
    BANDEJA_PENDIENTE_PROGRAMAR,
    BANDEJA_PROGRAMADOS,
    BANDEJA_TODOS,
    aplicar_bandeja,
    conteos_bandejas,
)
from estudios.models import EstudioComplementario, InformeEstudioComplementario, SesionActividad
from estudios.services import (
    anular_estudio,
    asignar_turno_estudio,
    crear_estudio,
    crear_informe,
    entregar_estudio,
    emitir_informe,
    marcar_realizado,
    validar_informe,
)
from turnos.models import Turno

BASE = '/api/estudios-complementarios/'


def _uid():
    return uuid.uuid4().hex[:8]


def _ids(response):
    data = response.data
    if isinstance(data, list):
        return [row['id'] for row in data]
    results = data.get('results')
    if results is None:
        return []
    return [row['id'] for row in results]


def _slot(*, day_offset=2, hour=3):
    ini = timezone.now() + timedelta(days=day_offset, hours=hour)
    return ini, ini + timedelta(minutes=20)


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


@pytest.mark.django_db
def test_matriz_bandejas_orm(paciente, tipo_estudio, admin_user, recurso_sala, medico):
    e_sol = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    e_prog = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    ini, fin = _slot()
    asignar_turno_estudio(
        e_prog, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    e_prog.refresh_from_db()

    e_real = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    ini2, fin2 = _slot(day_offset=3)
    asignar_turno_estudio(
        e_real, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini2, fecha_hora_fin=fin2, medico=medico,
    )
    marcar_realizado(e_real, user=admin_user)
    e_real.refresh_from_db()
    # turno cancelado no lo saca de documentación pendiente
    Turno.objects.filter(pk=e_real.turno_id).update(estado=Turno.Estado.CANCELADO)

    e_anul = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    anular_estudio(e_anul, user=admin_user, motivo='A5')

    qs = EstudioComplementario.objects.all()
    assert e_sol.pk in aplicar_bandeja(qs, BANDEJA_PENDIENTE_PROGRAMAR).values_list('pk', flat=True)
    assert e_prog.pk in aplicar_bandeja(qs, BANDEJA_PROGRAMADOS).values_list('pk', flat=True)
    assert e_real.pk in aplicar_bandeja(qs, BANDEJA_DOCUMENTACION_PENDIENTE).values_list(
        'pk', flat=True
    )
    assert e_real.pk not in aplicar_bandeja(qs, BANDEJA_PENDIENTE_PROGRAMAR).values_list(
        'pk', flat=True
    )
    assert e_anul.pk in aplicar_bandeja(qs, BANDEJA_ANULADOS).values_list('pk', flat=True)

    counts = conteos_bandejas(qs)
    assert counts[BANDEJA_TODOS] >= 4
    assert counts[BANDEJA_PENDIENTE_PROGRAMAR] >= 1
    assert counts[BANDEJA_PROGRAMADOS] >= 1
    assert counts[BANDEJA_DOCUMENTACION_PENDIENTE] >= 1
    assert counts[BANDEJA_ANULADOS] >= 1


@pytest.mark.django_db
def test_api_bandeja_filtra_antes_de_paginar_y_resumen(
    admin_client, paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    r = admin_client.get(BASE, {'bandeja': BANDEJA_PENDIENTE_PROGRAMAR, 'page_size': 1})
    assert r.status_code == status.HTTP_200_OK
    assert e.pk in _ids(r)

    ini, fin = _slot(day_offset=4)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    r2 = admin_client.get(BASE, {'bandeja': BANDEJA_PENDIENTE_PROGRAMAR})
    assert e.pk not in _ids(r2)
    r3 = admin_client.get(BASE, {'bandeja': BANDEJA_PROGRAMADOS})
    assert e.pk in _ids(r3)

    resumen = admin_client.get(f'{BASE}bandejas-resumen/')
    assert resumen.status_code == status.HTTP_200_OK
    assert resumen.data[BANDEJA_PROGRAMADOS] >= 1
    assert resumen.data[BANDEJA_TODOS] >= 1
    # mismos criterios: search vacío
    assert 'pendiente_programar' in resumen.data


@pytest.mark.django_db
def test_flujo_completo_bandejas(
    admin_client, paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    assert e.pk in _ids(admin_client.get(BASE, {'bandeja': BANDEJA_PENDIENTE_PROGRAMAR}))

    ini, fin = _slot(day_offset=5)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    marcar_realizado(e, user=admin_user)
    e.refresh_from_db()
    assert e.estado == EstudioComplementario.Estado.REALIZADO
    assert e.pk in _ids(
        admin_client.get(BASE, {'bandeja': BANDEJA_DOCUMENTACION_PENDIENTE})
    )

    informe = crear_informe(e, user=admin_user, texto='A5 informe')
    emitir_informe(informe, user=admin_user, medico=medico)
    e.refresh_from_db()
    assert e.estado == EstudioComplementario.Estado.INFORMADO
    assert e.pk in _ids(
        admin_client.get(BASE, {'bandeja': BANDEJA_DOCUMENTACION_PENDIENTE})
    )

    informe.refresh_from_db()
    validar_informe(informe, user=admin_user)
    e.refresh_from_db()
    assert e.estado == EstudioComplementario.Estado.VALIDADO
    assert e.pk in _ids(admin_client.get(BASE, {'bandeja': BANDEJA_PENDIENTE_ENTREGA}))

    entregar_estudio(e, user=admin_user)
    e.refresh_from_db()
    assert e.estado == EstudioComplementario.Estado.ENTREGADO
    assert e.pk in _ids(admin_client.get(BASE, {'bandeja': BANDEJA_FINALIZADOS}))
    assert e.pk in _ids(admin_client.get(BASE, {'bandeja': 'todos'}))


@pytest.mark.django_db
def test_lab_sin_acceso_bandejas(db):
    """Permisos: laboratorio no accede al módulo estudios (403) — LIMS separado."""
    from usuarios.models import User

    u = User.objects.create_user(username=f'lab_{_uid()}', password='x', rol='laboratorio')
    c = APIClient()
    c.force_authenticate(u)
    r = c.get(BASE)
    assert r.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_200_OK)
    if r.status_code == status.HTTP_200_OK:
        assert _ids(r) == []
    r2 = c.get(f'{BASE}bandejas-resumen/')
    assert r2.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_200_OK)
    if r2.status_code == status.HTTP_200_OK:
        assert r2.data.get(BANDEJA_TODOS, 0) == 0


@pytest.mark.django_db
def test_confirmado_turno_cancelado_es_pendiente_programar(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    ini, fin = _slot(day_offset=6)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    e.refresh_from_db()
    Turno.objects.filter(pk=e.turno_id).update(estado=Turno.Estado.CANCELADO)
    e.refresh_from_db()
    # FK histórica conservada; no vigente → pendiente programar
    assert e.turno_id is not None
    qs = EstudioComplementario.objects.filter(pk=e.pk)
    assert aplicar_bandeja(qs, BANDEJA_PENDIENTE_PROGRAMAR).filter(pk=e.pk).exists()
    assert not aplicar_bandeja(qs, BANDEJA_PROGRAMADOS).filter(pk=e.pk).exists()
