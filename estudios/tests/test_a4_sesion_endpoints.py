"""A4 — sesion_id, espejo multi D5, rechazo acciones legacy multi, TX/audit.

Multisesión solo vía fixtures ORM. Altas API siguen off. LIMS no se toca.
"""
from __future__ import annotations

import threading
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from estudios.actividad_rules import MSG_MULTI_ACCION_NO_SOPORTADA, MSG_SESION_INVALIDA
from estudios.models import EstudioComplementario, SesionActividad
from estudios.sesion_sync import sincronizar_espejo_turno
from estudios.services import (
    anular_estudio,
    asignar_turno_estudio,
    crear_estudio,
    crear_informe,
    marcar_realizado,
)
from turnos.models import Turno

BASE = '/api/estudios-complementarios/'


def _uid():
    return uuid.uuid4().hex[:8]


def _slot(*, day_offset: int = 2, hour: int = 3):
    inicio = timezone.now() + timedelta(days=day_offset, hours=hour)
    return inicio, inicio + timedelta(minutes=20)


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


def _fixture_multi(paciente, tipo_estudio, admin_user, *, n_sesiones=2):
    """Indicación multi + N sesiones (bypass clean de altas)."""
    e = EstudioComplementario(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        practica=tipo_estudio.practica,
        estado=EstudioComplementario.Estado.SOLICITADO,
        creado_por=admin_user,
        permite_multi_sesion=True,
        tipo_actividad=EstudioComplementario.TipoActividad.ESTUDIO,
    )
    e.save()
    sesiones = []
    for n in range(1, n_sesiones + 1):
        sesiones.append(
            SesionActividad.objects.create(
                estudio=e,
                numero_sesion=n,
                estado_sesion=SesionActividad.EstadoSesion.PENDIENTE,
            )
        )
    return e, sesiones


@pytest.mark.django_db
def test_mono_sin_sesion_id_intacta(paciente, tipo_estudio, admin_user, recurso_sala, medico):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    ini, fin = _slot()
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
    )
    e.refresh_from_db()
    s1 = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert e.turno_id == s1.turno_id == e.turno_id
    assert s1.estado_sesion == SesionActividad.EstadoSesion.PROGRAMADA


@pytest.mark.django_db
def test_mono_con_pk_sesion_uno_ok(paciente, tipo_estudio, admin_user, recurso_sala, medico):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    s1 = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    ini, fin = _slot(day_offset=3)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
        sesion_id=s1.pk,
    )
    e.refresh_from_db()
    s1.refresh_from_db()
    assert e.turno_id == s1.turno_id


@pytest.mark.django_db
def test_mono_sesion_id_ajeno_400_generico(
    paciente, tipo_estudio, admin_user, recurso_sala, medico, otro_paciente,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    e2 = crear_estudio(
        {
            'paciente': otro_paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    s_ajena = SesionActividad.objects.get(estudio=e2, numero_sesion=1)
    ini, fin = _slot(day_offset=4)
    with pytest.raises(DjangoValidationError) as exc:
        asignar_turno_estudio(
            e, user=admin_user, recurso=recurso_sala,
            fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
            sesion_id=s_ajena.pk,
        )
    assert MSG_SESION_INVALIDA in str(exc.value)
    e.refresh_from_db()
    assert e.turno_id is None


@pytest.mark.django_db
def test_mono_sesion_id_literal_uno_si_no_es_pk_falla(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    s1 = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    if s1.pk == 1:
        pytest.skip('PK casualmente 1; no valida el caso')
    ini, fin = _slot(day_offset=5)
    with pytest.raises(DjangoValidationError) as exc:
        asignar_turno_estudio(
            e, user=admin_user, recurso=recurso_sala,
            fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
            sesion_id=1,
        )
    assert MSG_SESION_INVALIDA in str(exc.value)


@pytest.mark.django_db
def test_multi_sin_sesion_id_rechaza(paciente, tipo_estudio, admin_user, recurso_sala, medico):
    e, _ = _fixture_multi(paciente, tipo_estudio, admin_user)
    ini, fin = _slot(day_offset=6)
    with pytest.raises(DjangoValidationError):
        asignar_turno_estudio(
            e, user=admin_user, recurso=recurso_sala,
            fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
        )
    e.refresh_from_db()
    assert e.turno_id is None
    assert not Turno.objects.filter(paciente=paciente).exists()


@pytest.mark.django_db
def test_multi_sesion_ajena_mismo_mensaje(
    paciente, tipo_estudio, admin_user, recurso_sala, medico, otro_paciente,
):
    e, sesiones = _fixture_multi(paciente, tipo_estudio, admin_user)
    e2, _ = _fixture_multi(otro_paciente, tipo_estudio, admin_user)
    s_ajena = SesionActividad.objects.filter(estudio=e2).first()
    ini, fin = _slot(day_offset=7)
    with pytest.raises(DjangoValidationError) as exc:
        asignar_turno_estudio(
            e, user=admin_user, recurso=recurso_sala,
            fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
            sesion_id=s_ajena.pk,
        )
    assert MSG_SESION_INVALIDA in str(exc.value)
    # inexistente
    with pytest.raises(DjangoValidationError) as exc2:
        asignar_turno_estudio(
            e, user=admin_user, recurso=recurso_sala,
            fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
            sesion_id=9_999_999,
        )
    assert MSG_SESION_INVALIDA in str(exc2.value)


@pytest.mark.django_db
def test_multi_assign_espejo_d5_y_espejo_null_no_bloquea(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e, sesiones = _fixture_multi(paciente, tipo_estudio, admin_user, n_sesiones=2)
    s1, s2 = sesiones
    assert e.turno_id is None  # espejo null; no bloquea con sesion_id

    ini, fin = _slot(day_offset=8, hour=2)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
        sesion_id=s1.pk,
    )
    e.refresh_from_db()
    s1.refresh_from_db()
    assert s1.turno_id is not None
    assert e.turno_id == s1.turno_id  # exactamente 1 vigente

    ini2, fin2 = _slot(day_offset=8, hour=6)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini2, fecha_hora_fin=fin2, medico=medico,
        sesion_id=s2.pk,
    )
    e.refresh_from_db()
    s1.refresh_from_db()
    s2.refresh_from_db()
    assert s1.turno_id and s2.turno_id
    assert e.turno_id is None  # >1 vigente → null; FKs históricas intactas


@pytest.mark.django_db
def test_espejo_cero_vigentes_null_conserva_fk(
    paciente, tipo_estudio, admin_user, recurso_sala,
):
    e, sesiones = _fixture_multi(paciente, tipo_estudio, admin_user, n_sesiones=1)
    s1 = sesiones[0]
    ini = timezone.now() + timedelta(days=9)
    t = Turno.objects.create(
        paciente=paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=ini + timedelta(minutes=20),
        estado=Turno.Estado.CANCELADO,
        motivo_reserva='hist',
    )
    s1.turno = t
    s1.save(update_fields=['turno', 'updated_at'])
    sincronizar_espejo_turno(e)
    e.refresh_from_db()
    s1.refresh_from_db()
    assert e.turno_id is None
    assert s1.turno_id == t.pk


@pytest.mark.django_db(transaction=True)
def test_concurrente_dos_sesiones_espejo_final(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    e, sesiones = _fixture_multi(paciente, tipo_estudio, admin_user, n_sesiones=2)
    s1, s2 = sesiones
    barrier = threading.Barrier(2)
    errors: list = []

    def worker(sesion, hour):
        try:
            connection.close()
            ini = timezone.now() + timedelta(days=10, hours=hour)
            fin = ini + timedelta(minutes=20)
            barrier.wait(timeout=10)
            asignar_turno_estudio(
                e, user=admin_user, recurso=recurso_sala,
                fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
                sesion_id=sesion.pk,
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker, args=(s1, 2))
    t2 = threading.Thread(target=worker, args=(s2, 8))
    t1.start()
    t2.start()
    t1.join(30)
    t2.join(30)
    assert not errors, errors
    e.refresh_from_db()
    s1.refresh_from_db()
    s2.refresh_from_db()
    assert s1.turno_id and s2.turno_id
    # Dos vigentes → espejo null (D5)
    assert e.turno_id is None


@pytest.mark.django_db
def test_multi_realizar_anular_informe_sin_escrituras(
    paciente, tipo_estudio, admin_user,
):
    e, _ = _fixture_multi(paciente, tipo_estudio, admin_user)
    snap = (
        e.estado,
        e.turno_id,
        e.fecha_realizacion,
        e.motivo_anulacion,
        e.updated_at,
    )
    with pytest.raises(DjangoValidationError) as ex1:
        marcar_realizado(e, user=admin_user)
    assert MSG_MULTI_ACCION_NO_SOPORTADA in str(ex1.value)
    with pytest.raises(DjangoValidationError) as ex2:
        anular_estudio(e, user=admin_user, motivo='x')
    assert MSG_MULTI_ACCION_NO_SOPORTADA in str(ex2.value)
    with pytest.raises(DjangoValidationError) as ex3:
        crear_informe(e, user=admin_user, texto='no')
    assert MSG_MULTI_ACCION_NO_SOPORTADA in str(ex3.value)
    e.refresh_from_db()
    assert (
        e.estado,
        e.turno_id,
        e.fecha_realizacion,
        e.motivo_anulacion,
        e.updated_at,
    ) == snap


@pytest.mark.django_db
def test_assign_rollback_si_falla_auditoria(
    paciente, tipo_estudio, admin_user, recurso_sala, medico, monkeypatch,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    turnos_antes = Turno.objects.count()

    def _boom(**kwargs):
        raise RuntimeError('audit-fail-a4')

    monkeypatch.setattr('estudios.services.AuditEvent.objects.create', _boom)
    ini, fin = _slot(day_offset=11)
    with pytest.raises(RuntimeError, match='audit-fail-a4'):
        asignar_turno_estudio(
            e, user=admin_user, recurso=recurso_sala,
            fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico,
        )
    e.refresh_from_db()
    assert e.turno_id is None
    assert e.estado == EstudioComplementario.Estado.SOLICITADO
    assert Turno.objects.count() == turnos_antes
    s1 = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s1.turno_id is None


@pytest.mark.django_db
def test_permiso_asignar_api(
    admin_client, admin_user, paciente, tipo_estudio, recurso_sala, medico, enfermeria,
):
    e = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    s1 = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    ini, fin = _slot(day_offset=12)
    r = admin_client.post(
        f'{BASE}{e.pk}/asignar-turno/',
        {
            'recurso_id': recurso_sala.id,
            'fecha_hora_inicio': ini.isoformat(),
            'fecha_hora_fin': fin.isoformat(),
            'medico_id': medico.id,
            'sesion_id': s1.pk,
        },
        format='json',
    )
    assert r.status_code == status.HTTP_200_OK, r.data

    e2 = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    c = APIClient()
    c.force_authenticate(enfermeria)
    ini2, fin2 = _slot(day_offset=13)
    r2 = c.post(
        f'{BASE}{e2.pk}/asignar-turno/',
        {
            'recurso_id': recurso_sala.id,
            'fecha_hora_inicio': ini2.isoformat(),
            'fecha_hora_fin': fin2.isoformat(),
        },
        format='json',
    )
    assert r2.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
    e2.refresh_from_db()
    assert e2.turno_id is None


@pytest.mark.django_db
def test_alta_api_multi_sigue_rechazada(admin_client, paciente, tipo_estudio):
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.id,
            'tipo_estudio': tipo_estudio.id,
            'practica': tipo_estudio.practica,
            'permite_multi_sesion': True,
        },
        format='json',
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
