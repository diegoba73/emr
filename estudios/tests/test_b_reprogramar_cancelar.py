"""B — Anular/liberar reserva, reprogramar, historial, guarda agenda, duración variable."""

from __future__ import annotations

import threading
import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from estudios.models import (
    EstudioComplementario,
    HistorialTurnoSesionActividad,
    SesionActividad,
)
from estudios.services import (
    anular_estudio,
    asignar_turno_estudio,
    crear_estudio,
    marcar_realizado,
    reprogramar_turno_estudio,
)
from turnos import turno_estado
from turnos.models import Recurso, Turno

BASE = '/api/estudios-complementarios/'
TURNOS = '/api/turnos/'


def _uid():
    return uuid.uuid4().hex[:8]


def _slot(*, day_offset: int = 5, hour: int = 4, minutes: int = 45):
    """Duración variable (no exige 20' de consultorio)."""
    inicio = timezone.now() + timedelta(days=day_offset, hours=hour)
    return inicio, inicio + timedelta(minutes=minutes)


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


@pytest.fixture
def estudio_confirmado(paciente, tipo_estudio, admin_user, recurso_sala, medico):
    e = crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    ini, fin = _slot(day_offset=8)
    asignar_turno_estudio(
        e,
        user=admin_user,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=fin,
        medico=medico,
    )
    e.refresh_from_db()
    return e


@pytest.mark.django_db
def test_anular_libera_reserva_vigente(estudio_confirmado, admin_user):
    e = estudio_confirmado
    turno_id = e.turno_id
    assert turno_id
    anular_estudio(e, user=admin_user, motivo='Paciente no asiste')
    e.refresh_from_db()
    t = Turno.objects.get(pk=turno_id)
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert e.estado == EstudioComplementario.Estado.ANULADO
    assert e.motivo_anulacion == 'Paciente no asiste'
    assert t.estado == Turno.Estado.CANCELADO
    assert s.turno_id == turno_id  # vínculo histórico
    assert s.estado_sesion == SesionActividad.EstadoSesion.CANCELADA


@pytest.mark.django_db
def test_anular_rechaza_post_realizado(estudio_confirmado, admin_user):
    e = estudio_confirmado
    marcar_realizado(e, user=admin_user)
    e.refresh_from_db()
    turno_id = e.turno_id
    with pytest.raises(ValidationError, match='Solicitado o Confirmado'):
        anular_estudio(e, user=admin_user, motivo='tarde')
    e.refresh_from_db()
    assert e.estado == EstudioComplementario.Estado.REALIZADO
    assert Turno.objects.get(pk=turno_id).estado == Turno.Estado.CONFIRMADO


@pytest.mark.django_db
def test_reprogramar_crea_historial_y_cancela_anterior(
    estudio_confirmado, admin_user, recurso_sala, medico,
):
    e = estudio_confirmado
    anterior_id = e.turno_id
    ini, fin = _slot(day_offset=10, hour=6, minutes=40)
    reprogramar_turno_estudio(
        e,
        user=admin_user,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=fin,
        motivo='Cambio de agenda',
        medico=medico,
    )
    e.refresh_from_db()
    assert e.turno_id != anterior_id
    assert Turno.objects.get(pk=anterior_id).estado == Turno.Estado.CANCELADO
    assert Turno.objects.get(pk=e.turno_id).estado == Turno.Estado.CONFIRMADO
    hist = HistorialTurnoSesionActividad.objects.get(turno_anterior_id=anterior_id)
    assert hist.turno_nuevo_id == e.turno_id
    assert hist.motivo == 'Cambio de agenda'
    assert hist.actor_id == admin_user.id


@pytest.mark.django_db
def test_reprogramar_fallida_conserva_reserva(
    estudio_confirmado, admin_user, recurso_sala, medico, paciente,
):
    e = estudio_confirmado
    anterior_id = e.turno_id
    ocupado_ini, ocupado_fin = _slot(day_offset=12, hour=2, minutes=30)
    Turno.objects.create(
        paciente=paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=ocupado_ini,
        fecha_hora_fin=ocupado_fin,
        estado=Turno.Estado.CONFIRMADO,
        medico=medico,
    )
    with pytest.raises(ValidationError):
        reprogramar_turno_estudio(
            e,
            user=admin_user,
            recurso=recurso_sala,
            fecha_hora_inicio=ocupado_ini,
            fecha_hora_fin=ocupado_fin,
            motivo='conflicto',
            medico=medico,
        )
    e.refresh_from_db()
    assert e.turno_id == anterior_id
    assert Turno.objects.get(pk=anterior_id).estado == Turno.Estado.CONFIRMADO
    assert HistorialTurnoSesionActividad.objects.count() == 0


@pytest.mark.django_db
def test_reprogramar_excluye_reserva_propia(
    estudio_confirmado, admin_user, recurso_sala, medico,
):
    """Puede reprogramar al mismo slot (excluye turno propio)."""
    e = estudio_confirmado
    t = Turno.objects.get(pk=e.turno_id)
    anterior_id = t.pk
    reprogramar_turno_estudio(
        e,
        user=admin_user,
        recurso=recurso_sala,
        fecha_hora_inicio=t.fecha_hora_inicio,
        fecha_hora_fin=t.fecha_hora_fin,
        motivo='Misma franja OK',
        medico=medico,
    )
    e.refresh_from_db()
    assert e.turno_id != anterior_id
    assert Turno.objects.get(pk=anterior_id).estado == Turno.Estado.CANCELADO


@pytest.mark.django_db
def test_guarda_agenda_rechaza_cancelar_reprogramar_generico(
    estudio_confirmado, admin_user, recurso_sala,
):
    e = estudio_confirmado
    t = Turno.objects.get(pk=e.turno_id)
    with pytest.raises(turno_estado.TurnoEstadoTransitionError, match='Estudios y procedimientos'):
        turno_estado.cancelar_turno(t, actor=admin_user, motivo='vía agenda')
    t.refresh_from_db()
    assert t.estado == Turno.Estado.CONFIRMADO

    ini, fin = _slot(day_offset=15, minutes=30)
    with pytest.raises(turno_estado.TurnoEstadoTransitionError, match='Estudios y procedimientos'):
        turno_estado.reprogramar_turno(
            t,
            actor=admin_user,
            fecha_hora_inicio=ini,
            fecha_hora_fin=fin,
            motivo='vía agenda',
            recurso=recurso_sala,
        )


@pytest.mark.django_db
def test_guarda_no_afecta_turno_consulta(paciente, medico, recurso, admin_user):
    t = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=timezone.now() + timedelta(days=3),
        fecha_hora_fin=timezone.now() + timedelta(days=3, minutes=20),
        estado=Turno.Estado.CONFIRMADO,
    )
    out = turno_estado.cancelar_turno(t, actor=admin_user, motivo='consulta OK')
    assert out.applied
    t.refresh_from_db()
    assert t.estado == Turno.Estado.CANCELADO


@pytest.mark.django_db
def test_api_anular_responde_anulado_y_libera_turno(admin_client, estudio_confirmado):
    """Regresión: response debe reflejar ANULADO (no instancia stale pre-service)."""
    e = estudio_confirmado
    turno_id = e.turno_id
    assert turno_id
    r = admin_client.post(
        f'{BASE}{e.id}/anular/',
        {'motivo_anulacion': 'API anular verif'},
        format='json',
    )
    assert r.status_code == 200, r.content
    assert r.data.get('estado') == EstudioComplementario.Estado.ANULADO
    assert r.data.get('motivo_anulacion') == 'API anular verif'
    e.refresh_from_db()
    assert e.estado == EstudioComplementario.Estado.ANULADO
    assert Turno.objects.get(pk=turno_id).estado == Turno.Estado.CANCELADO


@pytest.mark.django_db
def test_api_reprogramar_turno(admin_client, estudio_confirmado, recurso_sala):
    e = estudio_confirmado
    ini, fin = _slot(day_offset=11, hour=5, minutes=50)
    r = admin_client.post(
        f'{BASE}{e.id}/reprogramar-turno/',
        {
            'recurso_id': recurso_sala.id,
            'fecha_hora_inicio': ini.isoformat(),
            'fecha_hora_fin': fin.isoformat(),
            'motivo': 'API reprogram',
        },
        format='json',
    )
    assert r.status_code == 200, r.content
    e.refresh_from_db()
    assert e.turno_id
    assert HistorialTurnoSesionActividad.objects.filter(motivo='API reprogram').exists()


@pytest.mark.django_db
def test_api_turnos_cancelar_estudio_rechazado(admin_client, estudio_confirmado):
    t_id = estudio_confirmado.turno_id
    r = admin_client.post(
        f'{TURNOS}{t_id}/cancelar/',
        {'motivo': 'desde agenda'},
        format='json',
    )
    assert r.status_code == 400
    assert 'Estudios y procedimientos' in str(r.data)


@pytest.mark.django_db(transaction=True)
def test_competencia_sala_entre_estudios(
    paciente, tipo_estudio, admin_user, recurso_sala, medico,
):
    """Dos solicitudes distintas: una gana la sala; la otra falla y no deja parcial."""
    e1 = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    e2 = crear_estudio(
        {'paciente': paciente, 'tipo_estudio': tipo_estudio, 'practica': tipo_estudio.practica},
        user=admin_user,
    )
    ini, fin = _slot(day_offset=20, hour=1, minutes=35)
    barrier = threading.Barrier(2)
    results = {}

    def _run(key, estudio):
        connection.close()
        barrier.wait(timeout=10)
        try:
            asignar_turno_estudio(
                estudio,
                user=admin_user,
                recurso=recurso_sala,
                fecha_hora_inicio=ini,
                fecha_hora_fin=fin,
                medico=medico,
            )
            results[key] = 'ok'
        except Exception as exc:  # noqa: BLE001
            results[key] = type(exc).__name__

    t1 = threading.Thread(target=_run, args=('a', e1))
    t2 = threading.Thread(target=_run, args=('b', e2))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    assert sorted(results.values()) == sorted(['ok', 'ValidationError']) or (
        'ok' in results.values() and any(v != 'ok' for v in results.values())
    )
    confirmados = Turno.objects.filter(
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        estado=Turno.Estado.CONFIRMADO,
    ).count()
    assert confirmados == 1


@pytest.mark.django_db
def test_asignar_acepta_duracion_variable(estudio_solicitado, admin_user, recurso_sala, medico):
    ini, fin = _slot(minutes=55)
    asignar_turno_estudio(
        estudio_solicitado,
        user=admin_user,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=fin,
        medico=medico,
    )
    estudio_solicitado.refresh_from_db()
    t = Turno.objects.get(pk=estudio_solicitado.turno_id)
    assert (t.fecha_hora_fin - t.fecha_hora_inicio) == timedelta(minutes=55)


@pytest.mark.django_db
def test_api_desde_modulo_estudios_no_activable_por_payload_ni_query(
    admin_client, estudio_confirmado,
):
    """Flag interno: views no lo leen de body ni query; payload no bypassa la guarda."""
    t_id = estudio_confirmado.turno_id
    for payload in (
        {'motivo': 'bypass body', 'desde_modulo_estudios': True},
        {'motivo': 'bypass body str', 'desde_modulo_estudios': 'true'},
        {'motivo': 'bypass body 1', 'desde_modulo_estudios': 1},
    ):
        r = admin_client.post(f'{TURNOS}{t_id}/cancelar/', payload, format='json')
        assert r.status_code == 400, payload
        assert 'Estudios y procedimientos' in str(r.data)

    r_q = admin_client.post(
        f'{TURNOS}{t_id}/cancelar/?desde_modulo_estudios=true',
        {'motivo': 'bypass query'},
        format='json',
    )
    assert r_q.status_code == 400
    assert 'Estudios y procedimientos' in str(r_q.data)

    ini, fin = _slot(day_offset=16, minutes=30)
    r_rep = admin_client.post(
        f'{TURNOS}{t_id}/reprogramar/',
        {
            'fecha_hora_inicio': ini.isoformat(),
            'fecha_hora_fin': fin.isoformat(),
            'motivo': 'bypass reprogram',
            'desde_modulo_estudios': True,
        },
        format='json',
    )
    assert r_rep.status_code == 400
    assert 'Estudios y procedimientos' in str(r_rep.data)

    Turno.objects.get(pk=t_id).refresh_from_db()
    assert Turno.objects.get(pk=t_id).estado == Turno.Estado.CONFIRMADO


@pytest.mark.django_db
def test_movil_reprogramar_no_acepta_flag_desde_modulo(
    admin_user, estudio_confirmado, recurso_sala, medico,
):
    """Camino móvil llama reprogramar_turno sin kwarg; el flag en datos no aplica."""
    t = Turno.objects.get(pk=estudio_confirmado.turno_id)
    ini, fin = _slot(day_offset=17, minutes=30)
    # Simula lo que haría un cliente que mete el flag en el body: el servicio
    # solo recibe kwargs explícitos (como movil/views.py).
    with pytest.raises(turno_estado.TurnoEstadoTransitionError, match='Estudios y procedimientos'):
        turno_estado.reprogramar_turno(
            t,
            actor=admin_user,
            fecha_hora_inicio=ini,
            fecha_hora_fin=fin,
            motivo='móvil',
            recurso=recurso_sala,
            # no pasar desde_modulo_estudios → default False
        )
    t.refresh_from_db()
    assert t.estado == Turno.Estado.CONFIRMADO


@pytest.mark.django_db
def test_guarda_cubre_turno_historico_de_reprogramacion(
    estudio_confirmado, admin_user, recurso_sala, medico,
):
    """Tras reprogramar, turno_anterior solo vive en historial; la guarda lo contempla."""
    e = estudio_confirmado
    ini, fin = _slot(day_offset=18, hour=3, minutes=40)
    reprogramar_turno_estudio(
        e,
        user=admin_user,
        recurso=recurso_sala,
        fecha_hora_inicio=ini,
        fecha_hora_fin=fin,
        motivo='hist',
        medico=medico,
    )
    hist = HistorialTurnoSesionActividad.objects.get(motivo='hist')
    anterior = Turno.objects.get(pk=hist.turno_anterior_id)
    nuevo = Turno.objects.get(pk=hist.turno_nuevo_id)
    e.refresh_from_db()
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)

    # Consulta histórica preservada
    assert hist.turno_anterior_id == anterior.pk
    assert hist.turno_nuevo_id == nuevo.pk
    assert s.turno_id == nuevo.pk
    assert e.turno_id == nuevo.pk
    assert anterior.estado == Turno.Estado.CANCELADO
    assert not SesionActividad.objects.filter(turno_id=anterior.pk).exists()

    # Forzar estado no terminal para ejercer la guarda vía historial (no vía sesión).
    Turno.objects.filter(pk=anterior.pk).update(estado=Turno.Estado.CONFIRMADO)
    anterior.refresh_from_db()
    with pytest.raises(turno_estado.TurnoEstadoTransitionError, match='Estudios y procedimientos'):
        turno_estado.cancelar_turno(anterior, actor=admin_user, motivo='agenda sobre histórico')
    with pytest.raises(turno_estado.TurnoEstadoTransitionError, match='Estudios y procedimientos'):
        turno_estado.reprogramar_turno(
            anterior,
            actor=admin_user,
            fecha_hora_inicio=ini + timedelta(hours=2),
            fecha_hora_fin=fin + timedelta(hours=2),
            motivo='agenda sobre histórico',
            recurso=recurso_sala,
        )
    # Historial intacto tras intentos fallidos
    assert HistorialTurnoSesionActividad.objects.filter(pk=hist.pk).exists()
    hist.refresh_from_db()
    assert hist.turno_anterior_id == anterior.pk
