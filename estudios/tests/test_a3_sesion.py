"""A3 — SesionActividad, espejo mono histórico, sync TX, backfill.

No toca laboratorio/. Multisesión solo vía fixtures de modelo.
"""
from __future__ import annotations

import threading
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from estudios.models import EstudioComplementario, SesionActividad
from estudios.sesion_sync import backfill_sesiones_desde_estudios
from estudios.services import (
    anular_estudio,
    asignar_turno_estudio,
    crear_estudio,
    marcar_realizado,
)
from turnos.models import Turno

BASE = '/api/estudios-complementarios/'


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


def _slot(*, day_offset: int = 2, hour: int = 3, minutes: int = 20):
    """Duración 20' — validar_reserva exige la duración configurada del médico."""
    inicio = timezone.now() + timedelta(days=day_offset, hours=hour)
    return inicio, inicio + timedelta(minutes=minutes)


@pytest.mark.django_db
def test_crear_estudio_crea_sesion_uno(paciente, tipo_estudio, admin_user):
    e = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
            'origen': 'INTERNO',
        },
        user=admin_user,
    )
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s.turno_id is None
    assert s.estado_sesion == SesionActividad.EstadoSesion.PENDIENTE
    assert e.turno_id is None


@pytest.mark.django_db
def test_turno_realizado_conserva_vinculo_historico(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    ini, fin = _slot()
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    e.refresh_from_db()
    turno_id = e.turno_id
    assert turno_id
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s.turno_id == turno_id
    assert s.estado_sesion == SesionActividad.EstadoSesion.PROGRAMADA

    marcar_realizado(e, user=admin_user)
    e.refresh_from_db()
    s.refresh_from_db()
    assert e.turno_id == turno_id
    assert s.turno_id == turno_id
    assert s.estado_sesion == SesionActividad.EstadoSesion.REALIZADA
    assert s.fecha_realizacion == e.fecha_realizacion
    assert s.realizado_por_id == e.realizado_por_id == admin_user.id


@pytest.mark.django_db
def test_turno_cancelado_conserva_vinculo_historico(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    ini, fin = _slot(day_offset=3)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    e.refresh_from_db()
    turno_id = e.turno_id
    anular_estudio(e, user=admin_user, motivo='Prueba A3')
    e.refresh_from_db()
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert e.turno_id == turno_id
    assert s.turno_id == turno_id
    assert s.estado_sesion == SesionActividad.EstadoSesion.CANCELADA
    assert Turno.objects.get(pk=turno_id).estado == Turno.Estado.CANCELADO


@pytest.mark.django_db
def test_sync_fallo_revierte_asignacion(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    ini, fin = _slot(day_offset=4)
    turnos_antes = Turno.objects.count()
    with patch(
        'estudios.sesion_sync.sincronizar_espejo_turno',
        side_effect=RuntimeError('sync boom'),
    ):
        with pytest.raises(RuntimeError, match='sync boom'):
            asignar_turno_estudio(
                e, user=admin_user, recurso=recurso_sala,
                fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
            )
    e.refresh_from_db()
    assert e.turno_id is None
    assert e.estado == EstudioComplementario.Estado.SOLICITADO
    assert Turno.objects.count() == turnos_antes
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s.turno_id is None


@pytest.mark.django_db(transaction=True)
def test_asignaciones_concurrentes_sin_divergencia(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []

    def worker(offset_hours: int):
        try:
            connection.close()
            ini = timezone.now() + timedelta(days=6, hours=offset_hours)
            fin = ini + timedelta(minutes=20)
            barrier.wait(timeout=10)
            asignar_turno_estudio(
                e, user=admin_user, recurso=recurso_sala,
                fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
            )
            results.append('ok')
        except BaseException as exc:  # noqa: BLE001 — capturar para assert
            errors.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(5,))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    assert len(results) == 1, f'results={results!r} errors={errors!r}'
    assert len(errors) == 1, f'results={results!r} errors={errors!r}'
    e.refresh_from_db()
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert e.turno_id is not None
    assert s.turno_id == e.turno_id


@pytest.mark.django_db
def test_turno_no_puede_pertenecer_a_dos_sesiones(paciente, tipo_estudio, admin_user, recurso_sala):
    e1 = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        estado=EstudioComplementario.Estado.SOLICITADO,
        creado_por=admin_user,
    )
    e2 = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        estado=EstudioComplementario.Estado.SOLICITADO,
        creado_por=admin_user,
    )
    ini = timezone.now() + timedelta(days=4)
    turno = Turno.objects.create(
        paciente=paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=ini + timedelta(minutes=20),
        estado=Turno.Estado.CONFIRMADO,
        motivo_reserva='A3 constraint',
    )
    SesionActividad.objects.create(
        estudio=e1, numero_sesion=1, turno=turno,
        estado_sesion=SesionActividad.EstadoSesion.PROGRAMADA,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SesionActividad.objects.create(
                estudio=e2, numero_sesion=1, turno=turno,
                estado_sesion=SesionActividad.EstadoSesion.PROGRAMADA,
            )


@pytest.mark.django_db
def test_numero_sesion_unico_y_gte_uno(paciente, tipo_estudio, admin_user):
    e = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        estado=EstudioComplementario.Estado.SOLICITADO,
        creado_por=admin_user,
        permite_multi_sesion=True,  # fixture aislado; API sigue off
    )
    SesionActividad.objects.create(estudio=e, numero_sesion=1)
    SesionActividad.objects.create(estudio=e, numero_sesion=2)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SesionActividad.objects.create(estudio=e, numero_sesion=1)


@pytest.mark.django_db
def test_backfill_conserva_e_idempotente(paciente, tipo_estudio, admin_user, recurso_sala):
    ini = timezone.now() + timedelta(days=5)
    turno = Turno.objects.create(
        paciente=paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=ini + timedelta(minutes=20),
        estado=Turno.Estado.CONFIRMADO,
        motivo_reserva='backfill',
    )
    e = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        estado=EstudioComplementario.Estado.CONFIRMADO,
        turno=turno,
        fecha_realizacion=None,
        creado_por=admin_user,
    )
    assert not SesionActividad.objects.filter(estudio=e).exists()
    r1 = backfill_sesiones_desde_estudios()
    assert r1['creadas'] >= 1
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s.turno_id == turno.pk
    assert s.estado_sesion == SesionActividad.EstadoSesion.PROGRAMADA
    snap = (s.turno_id, s.estado_sesion, s.fecha_realizacion, s.realizado_por_id)
    r2 = backfill_sesiones_desde_estudios()
    assert r2['creadas'] == 0
    s.refresh_from_db()
    assert (s.turno_id, s.estado_sesion, s.fecha_realizacion, s.realizado_por_id) == snap


@pytest.mark.django_db
def test_get_no_modifica_datos(admin_client, paciente, tipo_estudio, admin_user):
    e = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        estado=EstudioComplementario.Estado.SOLICITADO,
        creado_por=admin_user,
    )
    assert SesionActividad.objects.filter(estudio=e).count() == 0
    before = list(
        EstudioComplementario.objects.filter(pk=e.pk).values(
            'turno_id', 'estado', 'fecha_realizacion', 'realizado_por_id', 'updated_at',
        )
    )[0]
    r = admin_client.get(f'{BASE}{e.pk}/')
    assert r.status_code == 200
    assert SesionActividad.objects.filter(estudio=e).count() == 0
    after = list(
        EstudioComplementario.objects.filter(pk=e.pk).values(
            'turno_id', 'estado', 'fecha_realizacion', 'realizado_por_id', 'updated_at',
        )
    )[0]
    assert before == after
