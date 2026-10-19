"""C — Procedimientos no quirúrgicos: alta, realización, Atencion/Registro, permisos."""

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
from catalogos.models import ProcedimientoCatalogo
from estudios.models import (
    ArchivoEstudioComplementario,
    EstudioComplementario,
    InformeEstudioComplementario,
    SesionActividad,
)
from estudios.services import (
    asignar_turno_estudio,
    crear_estudio,
    crear_informe,
    emitir_informe,
    entregar_estudio,
    marcar_realizado,
    rectificar_informe,
    validar_informe,
)
from medicos.models import Medico
from turnos.models import Atencion, RegistroProcedimiento
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
def proc_no_quir(db):
    return ProcedimientoCatalogo.objects.create(
        nombre=f'Proc NQ {_uid()}',
        clasificacion_quirurgica='NO_QUIRURGICO',
        activo=True,
    )


@pytest.fixture
def medico_con_user(db):
    u = User.objects.create_user(username=f'medc_{_uid()}', password='x', rol='medico')
    return Medico.objects.create(
        user=u, matricula=f'MC{_uid()}', nombre='Prof', apellido='Responsable',
    )


@pytest.fixture
def secretaria_client(secretaria):
    c = APIClient()
    c.force_authenticate(secretaria)
    return c


def _crear_proc(paciente, proc_no_quir, admin_user, medico=None):
    if medico is None:
        u = User.objects.create_user(username=f'pr_{_uid()}', password='x', rol='medico')
        medico = Medico.objects.create(
            user=u, matricula=f'PR{_uid()}', nombre='Prof', apellido='Proc',
        )
    return crear_estudio(
        {
            'paciente': paciente,
            'tipo_actividad': EstudioComplementario.TipoActividad.PROCEDIMIENTO,
            'procedimiento_catalogo': proc_no_quir,
            'medico_solicitante': medico,
            'origen': 'INTERNO',
        },
        user=admin_user,
    )


@pytest.mark.django_db
def test_alta_procedimiento_no_quirurgico(admin_client, paciente, proc_no_quir, medico_con_user):
    r = admin_client.post(
        BASE,
        {
            'paciente_id': paciente.id,
            'tipo_actividad': 'PROCEDIMIENTO',
            'procedimiento_catalogo': proc_no_quir.id,
            'medico_solicitante': medico_con_user.id,
            'origen': 'INTERNO',
        },
        format='json',
    )
    assert r.status_code == 201, r.content
    assert r.data['tipo_actividad'] == 'PROCEDIMIENTO'
    assert r.data['clasificacion_quirurgica_snapshot'] == 'NO_QUIRURGICO'
    assert r.data['procedimiento_catalogo'] == proc_no_quir.id
    assert r.data['medico_solicitante'] == medico_con_user.id


@pytest.mark.django_db
def test_realizar_sin_turno_ni_sala_sin_atencion(
    paciente, proc_no_quir, admin_user, medico_con_user,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    marcar_realizado(e, user=admin_user, profesional=medico_con_user)
    e.refresh_from_db()
    assert e.estado == 'REALIZADO'
    assert e.atencion_id is None
    assert e.realizado_por_id == medico_con_user.user_id
    assert e.modificado_por_id == admin_user.id
    assert not RegistroProcedimiento.objects.filter(
        atencion__paciente=paciente
    ).exists()
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s.estado_sesion == 'REALIZADA'
    assert s.atencion_id is None


@pytest.mark.django_db
def test_realizar_con_turno_crea_atencion_y_registro(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    ini = timezone.now() + timedelta(days=4, hours=2)
    fin = ini + timedelta(minutes=40)
    asignar_turno_estudio(
        e, user=admin_user, recurso=recurso_sala,
        fecha_hora_inicio=ini, fecha_hora_fin=fin, medico=medico_con_user,
    )
    e.refresh_from_db()
    marcar_realizado(e, user=admin_user, profesional=medico_con_user)
    e.refresh_from_db()
    assert e.atencion_id
    reg = RegistroProcedimiento.objects.get(pk=e.atencion_id)
    assert reg.procedimiento_id == proc_no_quir.id
    s = SesionActividad.objects.get(estudio=e, numero_sesion=1)
    assert s.atencion_id == e.atencion_id
    assert Atencion.objects.get(pk=e.atencion_id).tipo_intervencion == 'PROCEDIMIENTO'


@pytest.mark.django_db
def test_realizar_con_sala_sin_turno(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    marcar_realizado(
        e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
    )
    e.refresh_from_db()
    assert e.atencion_id
    assert RegistroProcedimiento.objects.filter(pk=e.atencion_id).exists()
    at = Atencion.objects.get(pk=e.atencion_id)
    assert at.turno_id is None


@pytest.mark.django_db
def test_secretaria_marca_realizado_profesional_distinto(
    paciente, proc_no_quir, admin_user, medico_con_user, secretaria,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    marcar_realizado(e, user=secretaria, profesional=medico_con_user)
    e.refresh_from_db()
    assert e.modificado_por_id == secretaria.id
    assert e.realizado_por_id == medico_con_user.user_id
    assert e.realizado_por_id != secretaria.id


@pytest.mark.django_db
def test_secretaria_valida_informe(
    secretaria_client, paciente, proc_no_quir, admin_user, medico_con_user,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    e = marcar_realizado(e, user=admin_user, profesional=medico_con_user)
    inf = crear_informe(e, user=admin_user, texto='hallazgos')
    emitir_informe(inf, user=admin_user, medico=medico_con_user)
    r = secretaria_client.post(f'{BASE}{e.id}/informes/{inf.id}/validar/', {}, format='json')
    assert r.status_code == 200, r.content
    e.refresh_from_db()
    assert e.estado == 'VALIDADO'


@pytest.mark.django_db
def test_idempotencia_marcar_realizado(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    marcar_realizado(
        e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
    )
    e.refresh_from_db()
    at_id = e.atencion_id
    marcar_realizado(
        e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
    )
    e.refresh_from_db()
    assert e.atencion_id == at_id
    assert RegistroProcedimiento.objects.filter(pk=at_id).count() == 1
    assert Atencion.objects.filter(paciente=paciente, tipo_intervencion='PROCEDIMIENTO').count() == 1


@pytest.mark.django_db
def test_informe_vincula_registro_cuando_existe(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    marcar_realizado(
        e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
    )
    e.refresh_from_db()
    inf = crear_informe(e, user=admin_user, texto='canónico')
    inf.refresh_from_db()
    assert inf.registro_procedimiento_id == e.atencion_id
    reg = RegistroProcedimiento.objects.get(pk=e.atencion_id)
    assert not (reg.informe_medico or '').strip()  # sin duplicar texto


@pytest.mark.django_db
def test_atencion_incompatible_bloquea(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso, recurso_sala,
):
    from turnos.models import ConsultaAmbulatoria

    e = _crear_proc(paciente, proc_no_quir, admin_user)
    at = Atencion.objects.create(
        paciente=paciente,
        medico_principal=medico_con_user,
        tipo_atencion='CONSULTORIO',
        tipo_intervencion='CONSULTA',
        contexto_atencion='AMBULATORIA',
    )
    ConsultaAmbulatoria.objects.create(atencion=at)
    e.atencion = at
    e.save(update_fields=['atencion', 'updated_at'])
    regs_antes = RegistroProcedimiento.objects.count()
    with pytest.raises(ValidationError, match='incompatible'):
        marcar_realizado(
            e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
        )
    e.refresh_from_db()
    assert e.estado == 'SOLICITADO'
    assert e.atencion_id == at.pk  # no reemplaza
    assert RegistroProcedimiento.objects.count() == regs_antes
    assert not RegistroProcedimiento.objects.filter(pk=at.pk).exists()


@pytest.mark.django_db
def test_filtro_tipo_actividad(admin_client, paciente, proc_no_quir, tipo_estudio, admin_user):
    _crear_proc(paciente, proc_no_quir, admin_user)
    crear_estudio(
        {
            'paciente': paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
        },
        user=admin_user,
    )
    r = admin_client.get(BASE, {'tipo_actividad': 'PROCEDIMIENTO'})
    assert r.status_code == 200
    results = r.data['results'] if isinstance(r.data, dict) else r.data
    assert results
    assert all(x['tipo_actividad'] == 'PROCEDIMIENTO' for x in results)


@pytest.mark.django_db
def test_informe_proc_emitir_validar_entregar_rectificar(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala, archivo_medico,
):
    """Circuito documental completo de PROCEDIMIENTO (con registro + archivo)."""
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    e = marcar_realizado(
        e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
    )
    ArchivoEstudioComplementario.objects.create(
        estudio=e,
        archivo_medico=archivo_medico,
        tipo_rol='OTRO',
        subido_por=admin_user,
    )
    assert ArchivoEstudioComplementario.objects.filter(estudio=e).count() == 1

    inf = crear_informe(e, user=admin_user, texto='hallazgos proc')
    emitir_informe(inf, user=admin_user, medico=medico_con_user)
    e.refresh_from_db()
    assert e.estado == 'INFORMADO'

    inf = validar_informe(inf, user=medico_con_user.user)
    e.refresh_from_db()
    assert e.estado == 'VALIDADO'
    assert inf.estado == InformeEstudioComplementario.EstadoInforme.VALIDADO

    e = entregar_estudio(e, user=admin_user)
    assert e.estado == 'ENTREGADO'

    # validar_informe re-lee el informe; usar la instancia vigente (VALIDADO).
    inf.refresh_from_db()
    nuevo = rectificar_informe(
        inf, user=admin_user, motivo='corrección', texto='v2',
    )
    emitir_informe(nuevo, user=admin_user, medico=medico_con_user)
    e.refresh_from_db()
    assert e.estado == 'INFORMADO'
    assert InformeEstudioComplementario.objects.filter(estudio=e).count() >= 2


@pytest.mark.django_db
def test_secretaria_emite_y_rectifica(
    secretaria_client, paciente, proc_no_quir, admin_user, medico_con_user,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    e = marcar_realizado(e, user=admin_user, profesional=medico_con_user)
    inf = crear_informe(e, user=admin_user, texto='x')
    r_em = secretaria_client.post(
        f'{BASE}{e.id}/informes/{inf.id}/emitir/', {}, format='json',
    )
    assert r_em.status_code == 200, r_em.content
    inf.refresh_from_db()

    validar_informe(inf, user=medico_con_user.user)
    e.refresh_from_db()
    e = entregar_estudio(e, user=admin_user)
    inf.refresh_from_db()
    r_rec = secretaria_client.post(
        f'{BASE}{e.id}/informes/{inf.id}/rectificar/',
        {'motivo_rectificacion': 'corrección secretaria', 'texto': 'y'},
        format='json',
    )
    assert r_rec.status_code == 201, r_rec.content
    assert r_rec.data.get('id')
    assert r_rec.data.get('id') != inf.id
    assert r_rec.data.get('estado') == 'BORRADOR'


@pytest.mark.django_db
def test_marcar_realizado_rollback_si_falla_auditoria(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala, monkeypatch,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    regs_antes = RegistroProcedimiento.objects.count()
    at_antes = Atencion.objects.count()

    def _boom(**kwargs):
        raise RuntimeError('audit-fail-c-realizado')

    monkeypatch.setattr('estudios.services.AuditEvent.objects.create', _boom)
    with pytest.raises(RuntimeError, match='audit-fail-c-realizado'):
        marcar_realizado(
            e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
        )
    e.refresh_from_db()
    assert e.estado == 'SOLICITADO'
    assert e.atencion_id is None
    assert RegistroProcedimiento.objects.count() == regs_antes
    assert Atencion.objects.count() == at_antes
    assert not AuditEvent.objects.filter(
        entity_id=str(e.pk), metadata__accion='estudio_marcar_realizado',
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrencia_marcar_realizado_no_duplica(
    paciente, proc_no_quir, admin_user, medico_con_user, recurso_sala,
):
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    barrier = threading.Barrier(2)
    results = {}

    def _run(key):
        connection.close()
        barrier.wait(timeout=10)
        try:
            marcar_realizado(
                e, user=admin_user, profesional=medico_con_user, recurso=recurso_sala,
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
    assert e.estado == 'REALIZADO'
    assert e.atencion_id
    assert RegistroProcedimiento.objects.filter(pk=e.atencion_id).count() == 1
    assert Atencion.objects.filter(
        paciente=paciente, tipo_intervencion='PROCEDIMIENTO',
    ).count() == 1


@pytest.mark.django_db
def test_circuito_sin_turno_ni_sala_con_informe(
    paciente, proc_no_quir, admin_user, medico_con_user, archivo_medico,
):
    """Sin Atencion/Registro: informe y archivo sobre la indicación."""
    e = _crear_proc(paciente, proc_no_quir, admin_user)
    e = marcar_realizado(e, user=admin_user, profesional=medico_con_user)
    assert e.atencion_id is None
    ArchivoEstudioComplementario.objects.create(
        estudio=e,
        archivo_medico=archivo_medico,
        tipo_rol='OTRO',
        subido_por=admin_user,
    )
    inf = crear_informe(e, user=admin_user, texto='sin atención')
    assert inf.registro_procedimiento_id is None
    emitir_informe(inf, user=admin_user, medico=medico_con_user)
    validar_informe(inf, user=medico_con_user.user)
    e.refresh_from_db()
    e = entregar_estudio(e, user=admin_user)
    assert e.estado == 'ENTREGADO'
