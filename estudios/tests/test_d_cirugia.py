"""D — Cirugía básica: alta, realización, protocolo, cierre, entrega, rectificación."""

from __future__ import annotations

import threading
import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from catalogos.models import (
    CirugiaAbordaje,
    CirugiaEspecialidad,
    CirugiaProcedimiento,
    ProcedimientoCatalogo,
)
from estudios.models import (
    EstudioComplementario,
    HistorialCierreEstudioComplementario,
    HistorialEntregaEstudioComplementario,
    InformeEstudioComplementario,
)
from estudios.services import (
    asignar_turno_estudio,
    cerrar_cirugia,
    crear_estudio,
    crear_informe,
    emitir_informe,
    entregar_estudio,
    marcar_realizado,
    rectificar_informe,
    validar_informe,
)
from medicos.models import Medico
from turnos.models import Atencion, Recurso, RegistroQuirurgico
from usuarios.models import User

BASE = '/api/estudios-complementarios/'


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(admin_user)
    return c


@pytest.fixture
def cirugia_catalogo(db):
    esp = CirugiaEspecialidad.objects.create(nombre=f'Esp {_uid()}', orden=1, activo=True)
    proc = CirugiaProcedimiento.objects.create(
        especialidad=esp, nombre=f'Proc {_uid()}', activo=True,
    )
    abr = CirugiaAbordaje.objects.create(
        procedimiento=proc, nombre=f'Abr {_uid()}', activo=True,
    )
    return {'especialidad': esp, 'procedimiento': proc, 'abordaje': abr}


@pytest.fixture
def proc_quir(cirugia_catalogo):
    """Compat nombre fixture: procedimiento jerárquico (no ProcedimientoCatalogo)."""
    return cirugia_catalogo['procedimiento']


@pytest.fixture
def medico_con_user(db):
    u = User.objects.create_user(username=f'medd_{_uid()}', password='x', rol='medico')
    return Medico.objects.create(
        user=u, matricula=f'MD{_uid()}', nombre='Cirujano', apellido='Resp',
    )


@pytest.fixture
def anestesista(db):
    u = User.objects.create_user(username=f'anes_{_uid()}', password='x', rol='medico')
    return Medico.objects.create(
        user=u, matricula=f'AN{_uid()}', nombre='Anest', apellido='Sista',
    )


@pytest.fixture
def secretaria_client(secretaria):
    c = APIClient()
    c.force_authenticate(secretaria)
    return c


@pytest.fixture
def recurso_quirofano(db):
    return Recurso.objects.create(
        nombre=f'Q {_uid()}',
        tipo_recurso=Recurso.TipoRecurso.QUIROFANO,
        activo=True,
    )


@pytest.fixture
def recurso_hemo(db):
    return Recurso.objects.create(
        nombre=f'H {_uid()}',
        tipo_recurso=Recurso.TipoRecurso.SALA_HEMODINAMIA,
        activo=True,
    )


def _crear_cirugia(paciente, proc_quir, admin_user, abordaje=None, *, cirujano=None, anestesista=None):
    if cirujano is None:
        u = User.objects.create_user(username=f'cir_{_uid()}', password='x', rol='medico')
        cirujano = Medico.objects.create(
            user=u, matricula=f'C{_uid()}', nombre='Cir', apellido='Auto',
        )
    if anestesista is None:
        u2 = User.objects.create_user(username=f'anp_{_uid()}', password='x', rol='medico')
        anestesista = Medico.objects.create(
            user=u2, matricula=f'AP{_uid()}', nombre='Anes', apellido='Prev',
        )
    return crear_estudio(
        {
            'paciente': paciente,
            'tipo_actividad': EstudioComplementario.TipoActividad.CIRUGIA,
            'cirugia_especialidad': proc_quir.especialidad,
            'cirugia_procedimiento': proc_quir,
            'cirugia_abordaje': abordaje,
            'medico_solicitante': cirujano,
            'anestesista_previsto': anestesista,
            'origen': 'INTERNO',
        },
        user=admin_user,
    )


def _realizar(e, *, admin_user, medico, anestesista, recurso):
    return marcar_realizado(
        e,
        user=admin_user,
        profesional=medico,
        anestesista=anestesista,
        diagnostico_preoperatorio='Dx pre real',
        recurso=recurso,
    )


def _protocolo_validado(e, *, admin_user, medico):
    inf = crear_informe(e, user=admin_user, texto='Protocolo quirúrgico completo')
    emitir_informe(inf, user=admin_user, medico=medico)
    inf = validar_informe(inf, user=medico.user)
    e.refresh_from_db()
    return inf


@pytest.mark.django_db
def test_alta_cirugia_ok(admin_client, paciente, cirugia_catalogo, medico_con_user, anestesista):
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.id,
            'tipo_actividad': 'CIRUGIA',
            'cirugia_especialidad': cirugia_catalogo['especialidad'].id,
            'cirugia_procedimiento': cirugia_catalogo['procedimiento'].id,
            'medico_solicitante': medico_con_user.id,
            'anestesista_previsto': anestesista.id,
            'origen': 'INTERNO',
        },
        format='json',
    )
    assert r.status_code == 201, r.data
    assert r.data['tipo_actividad'] == 'CIRUGIA'
    assert r.data['clasificacion_quirurgica_snapshot'] == 'QUIRURGICO'
    assert r.data['cirugia_procedimiento'] == cirugia_catalogo['procedimiento'].id
    assert r.data['medico_solicitante'] == medico_con_user.id
    assert r.data['anestesista_previsto'] == anestesista.id
    assert not r.data.get('cirugia_abordaje')


@pytest.mark.django_db
def test_alta_cirugia_con_abordaje(admin_client, paciente, cirugia_catalogo, medico_con_user, anestesista):
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.id,
            'tipo_actividad': 'CIRUGIA',
            'cirugia_especialidad': cirugia_catalogo['especialidad'].id,
            'cirugia_procedimiento': cirugia_catalogo['procedimiento'].id,
            'cirugia_abordaje': cirugia_catalogo['abordaje'].id,
            'medico_solicitante': medico_con_user.id,
            'anestesista_previsto': anestesista.id,
            'origen': 'INTERNO',
        },
        format='json',
    )
    assert r.status_code == 201, r.data
    assert r.data['cirugia_abordaje'] == cirugia_catalogo['abordaje'].id


@pytest.mark.django_db
def test_alta_cirugia_rechaza_sin_catalogo_jerarquico(admin_client, paciente, medico_con_user, anestesista, db):
    proc = ProcedimientoCatalogo.objects.create(
        nombre=f'NQ {_uid()}', clasificacion_quirurgica='NO_QUIRURGICO', activo=True,
    )
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.id,
            'tipo_actividad': 'CIRUGIA',
            'procedimiento_catalogo': proc.id,
            'medico_solicitante': medico_con_user.id,
            'anestesista_previsto': anestesista.id,
            'origen': 'INTERNO',
        },
        format='json',
    )
    assert r.status_code == 400
    assert 'cirugia_especialidad' in r.data or 'cirugia_procedimiento' in r.data


@pytest.mark.django_db
def test_alta_cirugia_rechaza_abordaje_de_otro_proc(
    admin_client, paciente, cirugia_catalogo, medico_con_user, anestesista, db,
):
    otra_esp = CirugiaEspecialidad.objects.create(nombre=f'Otra {_uid()}', activo=True)
    otro_proc = CirugiaProcedimiento.objects.create(
        especialidad=otra_esp, nombre=f'Otro {_uid()}', activo=True,
    )
    abr_ajeno = CirugiaAbordaje.objects.create(
        procedimiento=otro_proc, nombre=f'Abr ajeno {_uid()}', activo=True,
    )
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.id,
            'tipo_actividad': 'CIRUGIA',
            'cirugia_especialidad': cirugia_catalogo['especialidad'].id,
            'cirugia_procedimiento': cirugia_catalogo['procedimiento'].id,
            'cirugia_abordaje': abr_ajeno.id,
            'medico_solicitante': medico_con_user.id,
            'anestesista_previsto': anestesista.id,
            'origen': 'INTERNO',
        },
        format='json',
    )
    assert r.status_code == 400
    assert 'cirugia_abordaje' in r.data


@pytest.mark.django_db
def test_realizar_sin_turno_crea_atencion_rq(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    assert e.estado == 'REALIZADO'
    assert e.atencion_id
    assert not e.turno_id
    rq = RegistroQuirurgico.objects.get(pk=e.atencion_id)
    assert rq.anestesista_id == anestesista.pk
    assert rq.diagnostico_preoperatorio == 'Dx pre real'
    assert rq.protocolo_quirurgico == ''
    assert Atencion.objects.filter(pk=e.atencion_id, tipo_intervencion='CIRUGIA').exists()


@pytest.mark.django_db
def test_realizar_con_turno(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    inicio = timezone.now() + timedelta(hours=2)
    asignar_turno_estudio(
        e,
        user=admin_user,
        recurso=recurso_quirofano,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=inicio + timedelta(hours=1),
        medico=medico_con_user,
    )
    e.refresh_from_db()
    e = marcar_realizado(
        e,
        user=admin_user,
        profesional=medico_con_user,
        anestesista=anestesista,
        diagnostico_preoperatorio='Dx pre',
    )
    assert e.atencion_id
    assert RegistroQuirurgico.objects.filter(pk=e.atencion_id).count() == 1


@pytest.mark.django_db
def test_realizar_exige_anestesista(
    paciente, proc_quir, admin_user, medico_con_user, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    with pytest.raises(ValidationError):
        marcar_realizado(
            e,
            user=admin_user,
            profesional=medico_con_user,
            diagnostico_preoperatorio='Dx',
            recurso=recurso_quirofano,
        )


@pytest.mark.django_db
def test_documentacion_pendiente_sin_protocolo(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano, admin_client,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    r = admin_client.get(BASE, {'bandeja': 'documentacion_pendiente'})
    assert r.status_code == 200
    ids = [x['id'] for x in r.data.get('results', r.data)]
    assert e.id in ids


@pytest.mark.django_db
def test_cierre_requiere_protocolo_validado(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    with pytest.raises(ValidationError):
        cerrar_cirugia(e, user=admin_user)


@pytest.mark.django_db
def test_secretaria_emite_valida_y_cierra(
    paciente, proc_quir, admin_user, medico_con_user, anestesista,
    recurso_quirofano, secretaria_client, secretaria,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    inf = crear_informe(e, user=admin_user, texto='Protocolo OK')
    r_em = secretaria_client.post(f'{BASE}{e.id}/informes/{inf.id}/emitir/', {}, format='json')
    assert r_em.status_code == 200, r_em.content
    r_val = secretaria_client.post(f'{BASE}{e.id}/informes/{inf.id}/validar/', {}, format='json')
    assert r_val.status_code == 200, r_val.content
    e.refresh_from_db()
    inf.refresh_from_db()
    r_close = secretaria_client.post(f'{BASE}{e.id}/cerrar/', {}, format='json')
    assert r_close.status_code == 200, r_close.data
    e.refresh_from_db()
    assert e.cerrado_por_id == secretaria.id
    assert e.protocolo_cierre_informe_id == inf.pk
    assert HistorialCierreEstudioComplementario.objects.filter(estudio=e, informe=inf).count() == 1


@pytest.mark.django_db
def test_cierre_idempotente_y_entrega_vinculada(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    inf = _protocolo_validado(e, admin_user=admin_user, medico=medico_con_user)
    e.refresh_from_db()
    cerrar_cirugia(e, user=admin_user)
    e.refresh_from_db()
    n1 = HistorialCierreEstudioComplementario.objects.filter(estudio=e).count()
    cerrar_cirugia(e, user=admin_user)  # idempotente
    assert HistorialCierreEstudioComplementario.objects.filter(estudio=e).count() == n1
    e = entregar_estudio(e, user=admin_user)
    assert e.estado == 'ENTREGADO'
    assert HistorialEntregaEstudioComplementario.objects.filter(
        estudio=e, informe=inf,
    ).count() == 1


@pytest.mark.django_db
def test_rectificacion_exige_nuevo_cierre_antes_entrega(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    inf = _protocolo_validado(e, admin_user=admin_user, medico=medico_con_user)
    e.refresh_from_db()
    cerrar_cirugia(e, user=admin_user)
    e = entregar_estudio(e, user=admin_user)
    inf.refresh_from_db()
    nuevo = rectificar_informe(inf, user=admin_user, motivo='corrección', texto='Protocolo v2')
    emitir_informe(nuevo, user=admin_user, medico=medico_con_user)
    e.refresh_from_db()
    assert e.cerrado_por_id is None
    assert e.protocolo_cierre_informe_id is None
    assert HistorialCierreEstudioComplementario.objects.filter(estudio=e).count() >= 1
    nuevo = validar_informe(nuevo, user=medico_con_user.user)
    e.refresh_from_db()
    with pytest.raises(ValidationError):
        entregar_estudio(e, user=admin_user)
    cerrar_cirugia(e, user=admin_user)
    e = entregar_estudio(e, user=admin_user)
    assert e.estado == 'ENTREGADO'
    assert HistorialEntregaEstudioComplementario.objects.filter(estudio=e).count() >= 2
    assert HistorialCierreEstudioComplementario.objects.filter(estudio=e).count() >= 2


@pytest.mark.django_db
def test_proyeccion_protocolo_protegida_en_api(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano, admin_client,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    inf = _protocolo_validado(e, admin_user=admin_user, medico=medico_con_user)
    rq = RegistroQuirurgico.objects.get(pk=e.atencion_id)
    assert 'Protocolo' in rq.protocolo_quirurgico
    r = admin_client.put(
        f'/api/registros-quirurgicos/{rq.pk}/',
        {
            'anestesista_id': anestesista.pk,
            'diagnostico_preoperatorio': 'Dx pre real',
            'protocolo_quirurgico': 'INTENTO BYPASS',
        },
        format='multipart',
    )
    assert r.status_code == 400, r.data
    rq.refresh_from_db()
    assert rq.protocolo_quirurgico != 'INTENTO BYPASS'


@pytest.mark.django_db
def test_hemodinamia_cirugia_crea_rq_no_rp(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_hemo,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_hemo,
    )
    assert RegistroQuirurgico.objects.filter(pk=e.atencion_id).exists()
    from turnos.models import RegistroProcedimiento
    assert not RegistroProcedimiento.objects.filter(pk=e.atencion_id).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrencia_realizar_no_duplica(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    barrier = threading.Barrier(2)
    results = {}

    def _run(key):
        connection.close()
        barrier.wait(timeout=10)
        try:
            marcar_realizado(
                e,
                user=admin_user,
                profesional=medico_con_user,
                anestesista=anestesista,
                diagnostico_preoperatorio='Dx',
                recurso=recurso_quirofano,
            )
            results[key] = 'ok'
        except Exception as exc:  # noqa: BLE001
            results[key] = type(exc).__name__

    t1 = threading.Thread(target=_run, args=('a',))
    t2 = threading.Thread(target=_run, args=('b',))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    assert 'ok' in results.values()
    e.refresh_from_db()
    assert RegistroQuirurgico.objects.filter(pk=e.atencion_id).count() == 1
    assert Atencion.objects.filter(paciente=paciente, tipo_intervencion='CIRUGIA').count() == 1


@pytest.mark.django_db
def test_auditoria_cierre(
    paciente, proc_quir, admin_user, medico_con_user, anestesista, recurso_quirofano,
):
    e = _crear_cirugia(paciente, proc_quir, admin_user)
    e = _realizar(
        e, admin_user=admin_user, medico=medico_con_user,
        anestesista=anestesista, recurso=recurso_quirofano,
    )
    _protocolo_validado(e, admin_user=admin_user, medico=medico_con_user)
    e.refresh_from_db()
    cerrar_cirugia(e, user=admin_user)
    assert AuditEvent.objects.filter(
        entity_id=str(e.pk), metadata__accion='estudio_cerrar_cirugia',
    ).exists()
