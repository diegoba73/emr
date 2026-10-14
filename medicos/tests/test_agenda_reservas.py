from datetime import date, datetime, time, timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from medicos.models import Medico, DisponibilidadMedico, ExcepcionMedico
from pacientes.models import Paciente
from turnos.models import Turno, Recurso

pytestmark = pytest.mark.django_db

@pytest.fixture
def agenda():
    User = get_user_model()
    doctor = User.objects.create_user(username='agenda_med', rol='medico')
    med = Medico.objects.create(user=doctor, nombre='Med', apellido='Uno', matricula='AGENDA-1')
    other = Medico.objects.create(nombre='Med', apellido='Dos', matricula='AGENDA-2')
    admin = User.objects.create_user(username='agenda_admin', rol='admin')
    user = User.objects.create_user(username='agenda_pac', rol='paciente')
    pac = Paciente.objects.create(user=user, nombre='Paciente', apellido='Agenda', dni='AG-P1')
    fecha = timezone.localdate() + timedelta(days=7)
    inicio = timezone.make_aware(datetime.combine(fecha, time(9)))
    horario = DisponibilidadMedico.objects.create(medico=med, dia_semana=fecha.weekday(), hora_inicio=time(9), hora_fin=time(13))
    return med, other, doctor, admin, user, pac, fecha, inicio, horario


def client(user):
    c = APIClient(); c.force_authenticate(user=user); return c


def test_slots_20_min_sin_datos_de_otros_pacientes(agenda):
    med, _, _, _, user, pac, fecha, inicio, h = agenda
    Turno.objects.create(medico=med, paciente=pac, fecha_hora_inicio=inicio,
                         fecha_hora_fin=inicio+timedelta(minutes=20), estado='RESERVADO')
    r = client(user).get(f'/api/medicos/{med.pk}/slots/', {'fecha': fecha.isoformat()})
    assert r.status_code == 200
    assert len(r.data['slots']) == 11
    assert all(
        set(s) >= {'horario_id', 'inicio', 'fin', 'duracion_min', 'tipo', 'recurso_id', 'recurso_nombre'}
        for s in r.data['slots']
    )
    assert r.data['slots'][0]['duracion_min'] == 20
    assert r.data['slots'][0]['recurso_id'] is None


def test_dias_disponibles_paciente_ve_cupo_del_mes(agenda):
    med, other, _, _, user, pac, fecha, inicio, h = agenda
    c = client(user)
    desde = fecha.replace(day=1)
    if fecha.month == 12:
        hasta = fecha.replace(year=fecha.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        hasta = fecha.replace(month=fecha.month + 1, day=1) - timedelta(days=1)
    r = c.get(f'/api/medicos/{med.pk}/dias-disponibles/', {
        'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'tipo': 'CONSULTA',
    })
    assert r.status_code == 200, r.data
    fechas = {d['fecha'] for d in r.data['dias']}
    assert fecha.isoformat() in fechas
    assert all(d['cantidad_slots'] > 0 for d in r.data['dias'])
    # Solo días del weekday de la franja configurada
    assert all(date.fromisoformat(f).weekday() == fecha.weekday() for f in fechas)

    r = c.get(f'/api/medicos/{other.pk}/dias-disponibles/', {
        'desde': desde.isoformat(), 'hasta': hasta.isoformat(),
    })
    assert r.status_code == 200
    assert r.data['dias'] == []

    r = c.get(f'/api/medicos/{med.pk}/dias-disponibles/', {
        'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'tipo': 'ESTUDIO',
    })
    assert r.status_code == 200
    assert r.data['dias'] == []

    r = c.get(f'/api/medicos/{med.pk}/dias-disponibles/', {
        'desde': fecha.isoformat(),
        'hasta': (fecha + timedelta(days=70)).isoformat(),
    })
    assert r.status_code == 400


def test_paciente_reserva_propio_sin_consultorio_prioridad_y_no_duplica(agenda):
    med, _, _, _, user, pac, fecha, inicio, h = agenda
    c = client(user); data = {'horario_id':h.pk, 'inicio':inicio.isoformat()}
    r = c.post('/api/turnos/reservar-horario/', data, format='json')
    assert r.status_code == 201, r.data
    t = Turno.objects.get(pk=r.data['id'])
    assert t.paciente == pac and t.estado == 'RESERVADO' and t.recurso is None
    assert t.fecha_hora_fin-t.fecha_hora_inicio == timedelta(minutes=20)
    # Mismo horario ocupado / ya tiene turno activo
    r = c.post('/api/turnos/reservar-horario/', data, format='json')
    assert r.status_code == 400
    assert Turno.objects.count() == 1
    # Otro horario libre: tampoco puede (solo un turno activo; secretaría puede por /turnos/)
    otro = inicio + timedelta(minutes=20)
    r = c.post('/api/turnos/reservar-horario/', {'horario_id': h.pk, 'inicio': otro.isoformat()}, format='json')
    assert r.status_code == 400
    assert 'secretaría' in str(r.data).lower() or 'secretaria' in str(r.data).lower() or 'turno reservado' in str(r.data).lower()
    assert Turno.objects.count() == 1


@pytest.mark.parametrize('extra', [{'paciente_id':999}, {'recurso_id':1}, {'prioridad':'URGENTE'}, {'estado':'CONFIRMADO'}])
def test_paciente_no_puede_inyectar_campos(agenda, extra):
    *_, inicio, h = agenda
    r = client(agenda[4]).post('/api/turnos/reservar-horario/', {'horario_id':h.pk, 'inicio':inicio.isoformat(), **extra}, format='json')
    assert r.status_code == 400
    assert not Turno.objects.exists()


@pytest.mark.parametrize('minutes', [-20, 10, 240])
def test_no_reserva_fuera_de_franja_o_desalineado(agenda, minutes):
    *_, inicio, h = agenda
    r = client(agenda[4]).post('/api/turnos/reservar-horario/', {'horario_id':h.pk, 'inicio':(inicio+timedelta(minutes=minutes)).isoformat()}, format='json')
    assert r.status_code == 400


def test_cancelado_libera_slot_y_bloqueo_impide_reserva(agenda):
    med, _, _, _, user, pac, fecha, inicio, h = agenda
    t = Turno.objects.create(medico=med, paciente=pac, fecha_hora_inicio=inicio, fecha_hora_fin=inicio+timedelta(minutes=20), estado='CANCELADO')
    c = client(user)
    assert len(c.get(f'/api/medicos/{med.pk}/slots/', {'fecha':fecha.isoformat()}).data['slots']) == 12
    ExcepcionMedico.objects.create(medico=med, fecha=fecha, tipo='BLOQUEO')
    assert c.get(f'/api/medicos/{med.pk}/slots/', {'fecha':fecha.isoformat()}).data['slots'] == []
    assert c.post('/api/turnos/reservar-horario/', {'horario_id':h.pk,'inicio':inicio.isoformat()}, format='json').status_code == 400


def test_estudio_asigna_sala_configurada(agenda):
    med, _, _, _, user, pac, fecha, inicio, h = agenda
    sala = Recurso.objects.create(nombre='Sala agenda', ubicacion='CEHTA', tipo_recurso='SALA_PROCEDIMIENTO')
    h.tipo='ESTUDIO'; h.recurso=sala; h.save()
    r = client(user).get(f'/api/medicos/{med.pk}/slots/', {'fecha':fecha.isoformat(), 'tipo':'ESTUDIO'})
    assert len(r.data['slots']) == 12
    r = client(user).post('/api/turnos/reservar-horario/', {'horario_id':h.pk,'inicio':inicio.isoformat()}, format='json')
    assert r.status_code == 201, r.data
    assert Turno.objects.get(pk=r.data['id']).recurso == sala


def payload(med, dia=0):
    return {'medico':med.pk,'dia_semana':dia,'hora_inicio':'15:00','hora_fin':'17:00','duracion_slot_min':20,'tipo':'CONSULTA'}


@pytest.mark.parametrize('rol', ['secretaria', 'admin'])
def test_secretaria_admin_configuran_cualquier_medico(agenda, rol):
    med, other, _, _, _, _, fecha, _, _ = agenda
    user = get_user_model().objects.create_user(username='gestor_'+rol, rol=rol)
    c = client(user)
    for medico in [med, other]:
        r = c.post('/api/disponibilidades/', payload(medico), format='json')
        assert r.status_code == 201, r.data
        url = f"/api/disponibilidades/{r.data['id']}/"
        assert c.patch(url, {'hora_fin':'18:00'}, format='json').status_code == 200
        assert c.delete(url).status_code == 204
        r = c.post('/api/excepciones/', {'medico':medico.pk,'fecha':fecha.isoformat(),'tipo':'BLOQUEO'}, format='json')
        assert r.status_code == 201, r.data
        url = f"/api/excepciones/{r.data['id']}/"
        assert c.patch(url, {'motivo':'Ausencia'}, format='json').status_code == 200
        assert c.delete(url).status_code == 204


@pytest.mark.parametrize('rol', ['paciente', 'medico', 'enfermeria'])
def test_roles_no_autorizados_no_configuran(agenda, rol):
    u = get_user_model().objects.create_user(username='blocked_'+rol, rol=rol, is_staff=True)
    assert client(u).post('/api/disponibilidades/', payload(agenda[0]), format='json').status_code == 403


@pytest.mark.parametrize('changes', [{'hora_fin':'08:00'}, {'hora_inicio':'09:10'}, {'tipo':'ESTUDIO'}])
def test_validacion_horario(agenda, changes):
    r = client(agenda[3]).post('/api/disponibilidades/', {**payload(agenda[1]), **changes}, format='json')
    assert r.status_code == 400, r.data


def test_duracion_por_medico_genera_slots_y_reserva(agenda):
    med, _, _, admin, user, pac, fecha, inicio, h = agenda
    med.duracion_slot_min = 15
    med.save(update_fields=['duracion_slot_min'])
    h.hora_inicio = time(9, 0)
    h.hora_fin = time(10, 0)
    h.duracion_slot_min = 15
    h.save()
    r = client(user).get(f'/api/medicos/{med.pk}/slots/', {'fecha': fecha.isoformat()})
    assert r.status_code == 200
    assert len(r.data['slots']) == 4
    assert r.data['slots'][0]['duracion_min'] == 15
    r = client(user).post('/api/turnos/reservar-horario/', {
        'horario_id': h.pk, 'inicio': inicio.isoformat(),
    }, format='json')
    assert r.status_code == 201, r.data
    t = Turno.objects.get(pk=r.data['id'])
    assert t.fecha_hora_fin - t.fecha_hora_inicio == timedelta(minutes=15)


def test_configurar_semana_upsert_y_estudio_exige_sala(agenda):
    med, _, _, admin, _, _, _, _, h = agenda
    c = client(admin)
    sala = Recurso.objects.create(nombre='Sala semana', ubicacion='CEHTA', tipo_recurso='SALA_PROCEDIMIENTO')
    consultorio = Recurso.objects.create(nombre='Cons semana', ubicacion='CEHTA', tipo_recurso='CONSULTORIO')

    dias_off = [{'dia_semana': i, 'activo': False} for i in range(7)]
    dias_consulta = [
        {
            'dia_semana': i,
            'activo': i < 5,
            'hora_inicio': '09:00' if i < 5 else None,
            'hora_fin': '12:00' if i < 5 else None,
            'recurso': consultorio.pk if i < 5 else None,
        }
        for i in range(7)
    ]
    r = c.post('/api/disponibilidades/configurar-semana/', {
        'medico': med.pk,
        'tipo': 'CONSULTA',
        'duracion_slot_min': 30,
        'dias': dias_consulta,
    }, format='json')
    assert r.status_code == 200, r.data
    assert r.data['duracion_slot_min'] == 30
    assert len(r.data['horarios']) == 5
    med.refresh_from_db()
    assert med.duracion_slot_min == 30
    assert not DisponibilidadMedico.objects.filter(pk=h.pk).exists()

    r = c.post('/api/disponibilidades/configurar-semana/', {
        'medico': med.pk,
        'tipo': 'ESTUDIO',
        'dias': [
            {
                'dia_semana': i,
                'activo': i == 0,
                'hora_inicio': '14:00' if i == 0 else None,
                'hora_fin': '16:00' if i == 0 else None,
                'recurso': None,
            }
            for i in range(7)
        ],
    }, format='json')
    assert r.status_code == 400

    r = c.post('/api/disponibilidades/configurar-semana/', {
        'medico': med.pk,
        'tipo': 'ESTUDIO',
        'dias': [
            {
                'dia_semana': i,
                'activo': i == 0,
                'hora_inicio': '14:00' if i == 0 else None,
                'hora_fin': '16:00' if i == 0 else None,
                'recurso': sala.pk if i == 0 else None,
            }
            for i in range(7)
        ],
    }, format='json')
    assert r.status_code == 200, r.data
    assert len(r.data['horarios']) == 1
    assert r.data['horarios'][0]['recurso'] == sala.pk

    # Limpiar consultas: semana inactiva
    r = c.post('/api/disponibilidades/configurar-semana/', {
        'medico': med.pk, 'tipo': 'CONSULTA', 'dias': dias_off,
    }, format='json')
    assert r.status_code == 200, r.data
    assert r.data['horarios'] == []
    assert DisponibilidadMedico.objects.filter(medico=med, tipo='CONSULTA').count() == 0


def test_configurar_semana_roles_no_autorizados(agenda):
    med, _, _, _, user, _, _, _, _ = agenda
    dias = [{'dia_semana': i, 'activo': False} for i in range(7)]
    assert client(user).post('/api/disponibilidades/configurar-semana/', {
        'medico': med.pk, 'tipo': 'CONSULTA', 'dias': dias,
    }, format='json').status_code == 403


def test_staff_no_puede_reservar_fuera_horario_configurado(agenda):
    med, _, _, admin, _, pac, _, inicio, h = agenda
    data = {'medico_id':med.pk,'paciente_id':pac.pk,'fecha_hora_inicio':(inicio-timedelta(hours=1)).isoformat(),
            'fecha_hora_fin':(inicio-timedelta(minutes=40)).isoformat(),'estado':'RESERVADO'}
    assert client(admin).post('/api/turnos/', data, format='json').status_code == 400
    data.update(fecha_hora_inicio=inicio.isoformat(), fecha_hora_fin=(inicio+timedelta(minutes=20)).isoformat())
    r = client(admin).post('/api/turnos/', data, format='json')
    assert r.status_code == 201, r.data
    id = r.data['id']
    r = client(admin).post(f'/api/turnos/{id}/reprogramar/', {
        'fecha_hora_inicio':(inicio+timedelta(hours=5)).isoformat(),
        'fecha_hora_fin':(inicio+timedelta(hours=5, minutes=20)).isoformat(),'motivo':'Cambiar'}, format='json')
    assert r.status_code == 400
    assert Turno.objects.get(pk=id).fecha_hora_inicio == inicio


def test_sin_agenda_no_publica_slots_y_paciente_no_elude_calendario(agenda):
    med, other, _, _, user, pac, fecha, inicio, h = agenda
    c = client(user)
    assert c.get(f'/api/medicos/{other.pk}/slots/', {'fecha':fecha.isoformat()}).data['slots'] == []
    r = c.post('/api/turnos/', {'medico_id':other.pk,'paciente_id':pac.pk,
        'fecha_hora_inicio':inicio.isoformat(),'fecha_hora_fin':(inicio+timedelta(minutes=20)).isoformat(),'estado':'RESERVADO'}, format='json')
    assert r.status_code == 403


def test_recurso_ocupado_por_otro_medico_no_se_ofrece(agenda):
    med, other, _, _, user, pac, fecha, inicio, h = agenda
    sala = Recurso.objects.create(nombre='Compartida', ubicacion='CEHTA', tipo_recurso='CONSULTORIO')
    h.recurso=sala; h.save()
    Turno.objects.create(medico=other, paciente=pac, recurso=sala, fecha_hora_inicio=inicio,
                         fecha_hora_fin=inicio+timedelta(minutes=20), estado='CONFIRMADO')
    r = client(user).get(f'/api/medicos/{med.pk}/slots/', {'fecha':fecha.isoformat()})
    assert len(r.data['slots']) == 11
    assert client(user).post('/api/turnos/reservar-horario/', {'horario_id':h.pk,'inicio':inicio.isoformat()}, format='json').status_code == 400


def test_ajuste_horario_y_bloqueo_parcial(agenda):
    med, _, _, _, user, _, fecha, _, h = agenda
    ExcepcionMedico.objects.create(medico=med, fecha=fecha, tipo='AJUSTE', hora_inicio=time(15), hora_fin=time(16))
    ExcepcionMedico.objects.create(medico=med, fecha=fecha, tipo='BLOQUEO', hora_inicio=time(15,20), hora_fin=time(15,40))
    r = client(user).get(f'/api/medicos/{med.pk}/slots/', {'fecha':fecha.isoformat()})
    assert [timezone.localtime(datetime.fromisoformat(s['inicio'])).strftime('%H:%M') for s in r.data['slots']] == ['15:00','15:40']


def test_editar_motivo_no_cambia_duracion_de_turno_anterior(agenda):
    med, _, _, admin, _, pac, _, inicio, h = agenda
    t = Turno.objects.create(medico=med, paciente=pac, fecha_hora_inicio=inicio,
                             fecha_hora_fin=inicio+timedelta(minutes=60), estado='RESERVADO')
    r = client(admin).patch(f'/api/turnos/{t.pk}/', {'motivo_reserva':'Actualizado',
        'medico_id': med.pk, 'fecha_hora_inicio':inicio.isoformat(), 'fecha_hora_fin':t.fecha_hora_fin.isoformat()}, format='json')
    assert r.status_code == 200, r.data
    t.refresh_from_db()
    assert t.fecha_hora_fin-t.fecha_hora_inicio == timedelta(minutes=60)


def test_paciente_no_ve_reservas_ajenas(agenda):
    med, _, _, _, user, pac, _, inicio, h = agenda
    otro = Paciente.objects.create(nombre='Otro',apellido='Privado',dni='PRIVATE-AGENDA')
    Turno.objects.create(medico=med,paciente=otro,fecha_hora_inicio=inicio,
                        fecha_hora_fin=inicio+timedelta(minutes=20),estado='RESERVADO')
    r = client(user).get('/api/turnos/')
    rows = r.data.get('results', []) if isinstance(r.data,dict) else r.data
    assert rows == []


def test_medico_no_asigna_excepciones_ajenas_ni_se_reasigna_horario(agenda):
    med, other, doctor, _, _, _, fecha, _, h = agenda
    c = client(doctor)
    assert c.post('/api/excepciones/', {'medico':other.pk,'fecha':fecha.isoformat(),'tipo':'BLOQUEO'}, format='json').status_code == 403
    assert c.patch(f'/api/disponibilidades/{h.pk}/', {'medico':other.pk}, format='json').status_code == 403


def test_medico_no_modifica_ni_elimina_su_propia_agenda(agenda):
    med, _, doctor, _, _, _, fecha, _, h = agenda
    from django.contrib.auth.models import Group
    doctor.is_staff = True
    doctor.save()
    doctor.groups.add(Group.objects.get_or_create(name='Secretarias')[0])
    c = client(doctor)
    ex = ExcepcionMedico.objects.create(medico=med, fecha=fecha, tipo='BLOQUEO')
    for url in [f'/api/disponibilidades/{h.pk}/', f'/api/excepciones/{ex.pk}/']:
        assert c.get(url).status_code == 403
        assert c.patch(url, {}, format='json').status_code == 403
        assert c.delete(url).status_code == 403
    assert DisponibilidadMedico.objects.filter(pk=h.pk).exists()
    assert ExcepcionMedico.objects.filter(pk=ex.pk).exists()
