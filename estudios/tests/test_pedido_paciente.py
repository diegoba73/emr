"""Pedido de estudio paciente (foto) + tipificación/agenda secretaría + catálogo."""

from datetime import datetime, time, timedelta
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from estudios.models import (
    EstudioComplementario,
    MedicoTipoEstudio,
    PedidoEstudioPaciente,
    TipoEstudioComplementario,
    TipoEstudioSala,
)
from medicos.models import DisponibilidadMedico, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno
from turnos import turno_estado

pytestmark = pytest.mark.django_db
User = get_user_model()


def _img(name='pedido.jpg'):
    buf = BytesIO()
    Image.new('RGB', (32, 32), color=(200, 40, 40)).save(buf, format='JPEG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


@pytest.fixture
def ctx(db):
    pac_user = User.objects.create_user(username='pac_ped', password='x', rol='paciente')
    pac = Paciente.objects.create(user=pac_user, nombre='Ana', apellido='Pedido', dni='PED-1')
    sec = User.objects.create_user(username='sec_ped', password='x', rol='secretaria')
    admin = User.objects.create_user(username='adm_ped', password='x', rol='admin', is_staff=True)
    med = Medico.objects.create(nombre='Med', apellido='Estudio', matricula='PED-M1', duracion_slot_min=20)
    sala = Recurso.objects.create(
        nombre='Sala Ped',
        ubicacion='CEHTA',
        tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
        activo=True,
    )
    tipo = TipoEstudioComplementario.objects.create(
        codigo='PED-ECO',
        nombre='Eco pedido',
        practica=TipoEstudioComplementario.Modalidad.IMAGEN_US,
        activo=True,
    )
    fecha = timezone.localdate() + timedelta(days=7)
    while fecha.weekday() != 0:
        fecha += timedelta(days=1)
    DisponibilidadMedico.objects.create(
        medico=med,
        dia_semana=fecha.weekday(),
        hora_inicio=time(9, 0),
        hora_fin=time(12, 0),
        tipo='ESTUDIO',
        recurso=sala,
        activo=True,
    )
    MedicoTipoEstudio.objects.create(medico=med, tipo_estudio=tipo)
    TipoEstudioSala.objects.create(tipo_estudio=tipo, recurso=sala)
    inicio = timezone.make_aware(datetime.combine(fecha, time(9, 0)))
    return {
        'pac_user': pac_user,
        'pac': pac,
        'sec': sec,
        'admin': admin,
        'med': med,
        'sala': sala,
        'tipo': tipo,
        'inicio': inicio,
        'fecha': fecha,
    }


def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _seed_pedido_pendiente(ctx, *, notas='', origen='MOVIL'):
    """Pedidos legacy en DB (el alta por paciente/app está deshabilitada)."""
    return PedidoEstudioPaciente.objects.create(
        paciente=ctx['pac'],
        foto=_img(),
        origen_canal=origen,
        notas=notas,
        creado_por=ctx['pac_user'],
        estado=PedidoEstudioPaciente.Estado.PENDIENTE,
    )


def _pedido_agendado(ctx):
    pedido = _seed_pedido_pendiente(ctx)
    ag = client(ctx['sec']).post(
        f'/api/estudios-complementarios/pedidos/{pedido.id}/agendar/',
        {
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': ctx['med'].id,
            'inicio': ctx['inicio'].isoformat(),
        },
        format='json',
    )
    assert ag.status_code == 200, ag.data
    pedido.refresh_from_db()
    turno = Turno.objects.get(pk=pedido.turno_id)
    return pedido, turno


def test_paciente_no_crea_pedido_portal(ctx):
    c = client(ctx['pac_user'])
    r = c.post(
        '/api/estudios-complementarios/pedidos/',
        {'foto': _img(), 'origen_canal': 'PORTAL', 'notas': 'pedido papel'},
        format='multipart',
    )
    assert r.status_code == 403
    assert not PedidoEstudioPaciente.objects.filter(paciente=ctx['pac']).exists()


def test_admin_no_crea_pedido(ctx):
    c = client(ctx['admin'])
    r = c.post(
        '/api/estudios-complementarios/pedidos/',
        {'foto': _img(), 'origen_canal': 'PORTAL'},
        format='multipart',
    )
    assert r.status_code == 403


def test_secretaria_agenda_pedido(ctx):
    pedido = _seed_pedido_pendiente(ctx)
    c = client(ctx['sec'])
    r = c.post(
        f'/api/estudios-complementarios/pedidos/{pedido.id}/agendar/',
        {
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': ctx['med'].id,
            'inicio': ctx['inicio'].isoformat(),
        },
        format='json',
    )
    assert r.status_code == 200, r.data
    assert r.data['estado'] == 'AGENDADO'
    pedido.refresh_from_db()
    assert pedido.turno_id
    turno = Turno.objects.get(pk=pedido.turno_id)
    assert turno.estado == Turno.Estado.RESERVADO
    assert turno.paciente_id == ctx['pac'].id
    assert turno_estado.puede_reprogramar_turno(ctx['pac_user'], turno) is False
    assert turno_estado.puede_confirmar_turno(ctx['pac_user'], turno) is False
    assert turno_estado.puede_reprogramar_turno(ctx['sec'], turno) is True
    assert turno_estado.puede_confirmar_turno(ctx['sec'], turno) is True


def test_agenda_rechaza_medico_sin_catalogo(ctx):
    otro = Medico.objects.create(nombre='Otro', apellido='Sin', matricula='PED-M2')
    pedido = _seed_pedido_pendiente(ctx)
    c = client(ctx['sec'])
    r = c.post(
        f'/api/estudios-complementarios/pedidos/{pedido.id}/agendar/',
        {
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': otro.id,
            'inicio': ctx['inicio'].isoformat(),
        },
        format='json',
    )
    assert r.status_code == 400


def test_paciente_no_reprograma_ni_confirma_turno_de_pedido(ctx):
    pedido, turno = _pedido_agendado(ctx)
    nuevo_inicio = ctx['inicio'] + timedelta(minutes=20)
    r_rep = client(ctx['pac_user']).post(
        f'/api/turnos/{turno.id}/reprogramar/',
        {
            'fecha_hora_inicio': nuevo_inicio.isoformat(),
            'fecha_hora_fin': (nuevo_inicio + timedelta(minutes=20)).isoformat(),
            'motivo': 'Otro horario',
            'recurso_id': ctx['sala'].id,
        },
        format='json',
    )
    assert r_rep.status_code == 403, r_rep.data
    r_conf = client(ctx['pac_user']).post(f'/api/turnos/{turno.id}/confirmar/', {}, format='json')
    assert r_conf.status_code == 403, r_conf.data
    turno.refresh_from_db()
    pedido.refresh_from_db()
    assert turno.estado == Turno.Estado.RESERVADO
    assert pedido.turno_id == turno.id


def test_secretaria_reprograma_turno_de_pedido(ctx):
    pedido, turno = _pedido_agendado(ctx)
    nuevo_inicio = ctx['inicio'] + timedelta(minutes=20)
    nuevo_fin = nuevo_inicio + timedelta(minutes=20)
    outcome = turno_estado.reprogramar_turno(
        turno,
        actor=ctx['sec'],
        fecha_hora_inicio=nuevo_inicio,
        fecha_hora_fin=nuevo_fin,
        motivo='Otro horario secretaría',
        recurso=ctx['sala'],
    )
    assert outcome.applied
    pedido.refresh_from_db()
    assert pedido.turno_id == outcome.turno.pk
    assert outcome.turno.estado == Turno.Estado.RESERVADO
    assert outcome.turno.requiere_aceptacion_paciente is True
    from estudios.pedido_paciente import turno_viene_de_pedido_paciente

    assert turno_viene_de_pedido_paciente(outcome.turno) is True
    # Paciente puede aceptar el horario reprogramado (excepción a «estudios no confirma»).
    assert turno_estado.puede_confirmar_turno(ctx['pac_user'], outcome.turno) is True


def test_catalogo_medico_tipo_crud(ctx):
    c = client(ctx['sec'])
    r = c.get('/api/estudios-complementarios/medico-tipos/')
    assert r.status_code == 200
    data = r.data['results'] if isinstance(r.data, dict) else r.data
    assert any(row['medico'] == ctx['med'].id for row in data)


def test_paciente_no_ve_pedido_ajeno_ni_foto(ctx):
    pedido = _seed_pedido_pendiente(ctx)
    pid = pedido.id
    otro_user = User.objects.create_user(username='pac_otro_ped', password='x', rol='paciente')
    Paciente.objects.create(user=otro_user, nombre='Otro', apellido='Pac', dni='PED-2')
    c_otro = client(otro_user)
    assert c_otro.get(f'/api/estudios-complementarios/pedidos/{pid}/').status_code in (403, 404)
    assert c_otro.get(f'/api/estudios-complementarios/pedidos/{pid}/download-foto/').status_code in (
        403,
        404,
    )


def test_alta_directa_estudio_confirmada_y_rechazos_catalogo(ctx):
    c = client(ctx['sec'])
    r_ok = c.post(
        '/api/estudios-complementarios/agendar-turno/',
        {
            'paciente_id': ctx['pac'].id,
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': ctx['med'].id,
            'recurso_id': ctx['sala'].id,
            'origen': 'EXTERNO',
            'fecha_hora_inicio': (ctx['inicio'] + timedelta(minutes=40)).isoformat(),
            'fecha_hora_fin': (ctx['inicio'] + timedelta(minutes=60)).isoformat(),
        },
        format='json',
    )
    assert r_ok.status_code == 201, r_ok.data
    assert r_ok.data['estado'] == 'CONFIRMADO'
    assert r_ok.data['turno_id']

    otro = Medico.objects.create(nombre='Sin', apellido='Cat', matricula='PED-M3')
    r_bad = c.post(
        '/api/estudios-complementarios/agendar-turno/',
        {
            'paciente_id': ctx['pac'].id,
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': otro.id,
            'recurso_id': ctx['sala'].id,
            'origen': 'EXTERNO',
            'fecha_hora_inicio': (ctx['inicio'] + timedelta(hours=2)).isoformat(),
            'fecha_hora_fin': (ctx['inicio'] + timedelta(hours=2, minutes=20)).isoformat(),
        },
        format='json',
    )
    assert r_bad.status_code == 400

    sala_mala = Recurso.objects.create(
        nombre='Sala mala',
        ubicacion='CEHTA',
        tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
        activo=True,
    )
    r_sala = c.post(
        '/api/estudios-complementarios/agendar-turno/',
        {
            'paciente_id': ctx['pac'].id,
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': ctx['med'].id,
            'recurso_id': sala_mala.id,
            'origen': 'EXTERNO',
            'fecha_hora_inicio': (ctx['inicio'] + timedelta(hours=3)).isoformat(),
            'fecha_hora_fin': (ctx['inicio'] + timedelta(hours=3, minutes=20)).isoformat(),
        },
        format='json',
    )
    assert r_sala.status_code == 400


def test_pedido_alta_paciente_rechazada_sin_persistir(ctx):
    r = client(ctx['pac_user']).post(
        '/api/estudios-complementarios/pedidos/',
        {'origen_canal': 'PORTAL', 'notas': 'sin foto'},
        format='multipart',
    )
    assert r.status_code == 403
    assert not PedidoEstudioPaciente.objects.filter(paciente=ctx['pac'], notas='sin foto').exists()


def test_alta_tipificada_sin_franja_estudio_rechaza(ctx):
    """Catálogo OK pero sin franja ESTUDIO publicada → no crea turno ni estudio."""
    med_sin = Medico.objects.create(nombre='Sin', apellido='Franja', matricula='PED-M-NF')
    MedicoTipoEstudio.objects.create(medico=med_sin, tipo_estudio=ctx['tipo'])
    n_est = EstudioComplementario.objects.count()
    n_tur = Turno.objects.count()
    r = client(ctx['sec']).post(
        '/api/estudios-complementarios/agendar-turno/',
        {
            'paciente_id': ctx['pac'].id,
            'tipo_estudio': ctx['tipo'].id,
            'medico_id': med_sin.id,
            'recurso_id': ctx['sala'].id,
            'origen': 'EXTERNO',
            'fecha_hora_inicio': ctx['inicio'].isoformat(),
            'fecha_hora_fin': (ctx['inicio'] + timedelta(minutes=20)).isoformat(),
        },
        format='json',
    )
    assert r.status_code == 400, r.data
    assert EstudioComplementario.objects.count() == n_est
    assert Turno.objects.count() == n_tur


def test_asignar_turno_estudio_existente_exige_franja(ctx):
    from django.core.exceptions import ValidationError

    from estudios import services

    med_sin = Medico.objects.create(nombre='Sin', apellido='FranjaAsig', matricula='PED-M-NF2')
    MedicoTipoEstudio.objects.create(medico=med_sin, tipo_estudio=ctx['tipo'])
    estudio_sin = services.crear_estudio(
        {
            'paciente': ctx['pac'],
            'tipo_estudio': ctx['tipo'],
            'practica': ctx['tipo'].practica,
            'origen': EstudioComplementario.Origen.EXTERNO,
        },
        user=ctx['sec'],
    )
    n_tur = Turno.objects.count()
    with pytest.raises(ValidationError):
        services.asignar_turno_estudio(
            estudio_sin,
            user=ctx['sec'],
            recurso=ctx['sala'],
            fecha_hora_inicio=ctx['inicio'],
            fecha_hora_fin=ctx['inicio'] + timedelta(minutes=20),
            medico=med_sin,
        )
    estudio_sin.refresh_from_db()
    assert estudio_sin.turno_id is None
    assert estudio_sin.estado == EstudioComplementario.Estado.SOLICITADO
    assert Turno.objects.count() == n_tur

    estudio = services.crear_estudio(
        {
            'paciente': ctx['pac'],
            'tipo_estudio': ctx['tipo'],
            'practica': ctx['tipo'].practica,
            'origen': EstudioComplementario.Origen.EXTERNO,
        },
        user=ctx['sec'],
    )
    # Con franja válida del ctx → OK
    services.asignar_turno_estudio(
        estudio,
        user=ctx['sec'],
        recurso=ctx['sala'],
        fecha_hora_inicio=ctx['inicio'] + timedelta(minutes=60),
        fecha_hora_fin=ctx['inicio'] + timedelta(minutes=80),
        medico=ctx['med'],
    )
    estudio.refresh_from_db()
    assert estudio.turno_id
    assert estudio.estado == EstudioComplementario.Estado.CONFIRMADO


def test_slots_reprogramacion_filtra_sala_y_rechaza_paciente(ctx):
    _pedido, turno = _pedido_agendado(ctx)
    # Segunda sala ESTUDIO del mismo médico, no asociada al tipo → no debe ofrecerse
    sala_otra = Recurso.objects.create(
        nombre='Sala otra',
        ubicacion='CEHTA',
        tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
        activo=True,
    )
    DisponibilidadMedico.objects.create(
        medico=ctx['med'],
        dia_semana=ctx['fecha'].weekday(),
        hora_inicio=time(14, 0),
        hora_fin=time(16, 0),
        tipo='ESTUDIO',
        recurso=sala_otra,
        activo=True,
    )
    # Paciente ya no reprograma estudios.
    r_pac = client(ctx['pac_user']).get(
        f'/api/turnos/{turno.id}/slots-reprogramacion/',
        {'fecha': ctx['fecha'].isoformat()},
    )
    assert r_pac.status_code == 403

    r = client(ctx['sec']).get(
        f'/api/turnos/{turno.id}/slots-reprogramacion/',
        {'fecha': ctx['fecha'].isoformat()},
    )
    assert r.status_code == 200, r.data
    slots = r.data['slots']
    assert slots
    assert all(s['recurso_id'] == ctx['sala'].id for s in slots)
    assert not any(s['recurso_id'] == sala_otra.id for s in slots)


def test_paciente_lista_sus_pedidos_legacy(ctx):
    pedido = _seed_pedido_pendiente(ctx, notas='ver listado', origen='PORTAL')
    c = client(ctx['pac_user'])
    r = c.get('/api/estudios-complementarios/pedidos/')
    assert r.status_code == 200
    rows = r.data['results'] if isinstance(r.data, dict) else r.data
    assert any(p['id'] == pedido.id and p['estado'] == 'PENDIENTE' for p in rows)
