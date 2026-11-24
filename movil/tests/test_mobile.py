from datetime import timedelta
from unittest.mock import patch, Mock
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from pacientes.models import Paciente
from medicos.models import Medico
from turnos.models import Turno
from movil.models import SesionMovil, DispositivoPush, RecordatorioTurno
from movil.authentication import token_hash
from movil.recordatorios import preparar_recordatorios, enviar_pendientes

pytestmark = pytest.mark.django_db

@pytest.fixture
def data():
    cache.clear()
    from pacientes.tests.os_helpers import os_ref

    U = get_user_model()
    u = U.objects.create_user(username='mobilepatient', password='test-password', rol='paciente')
    p = Paciente.objects.create(
        user=u,
        nombre='Paciente',
        apellido='Privado',
        dni='MOB-1',
        obra_social=os_ref('PARTICULAR'),
    )
    d = U.objects.create_user(username='mobiledoc', password='test-password', rol='medico')
    m = Medico.objects.create(user=d, nombre='Medico', apellido='Uno', matricula='MOB-1')
    start = timezone.now() + timedelta(hours=23)
    t = Turno.objects.create(paciente=p, medico=m, fecha_hora_inicio=start,
        fecha_hora_fin=start+timedelta(minutes=20), estado='CONFIRMADO')
    c = APIClient()
    r = c.post('/api/movil/login/', {'username':u.username,'password':'test-password'}, format='json')
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION='Bearer '+r.data['token'])
    s = SesionMovil.objects.get(user=u)
    device = DispositivoPush.objects.create(sesion=s, token='ExpoPushToken[testing]', plataforma='android')
    return c,u,d,t,s,device,r.data['token']

def test_login_hash_logout_and_expiry(data):
    c,u,d,t,s,device,token = data
    assert s.token_hash == token_hash(token) and s.token_hash != token
    assert c.get('/api/movil/me/').status_code == 200
    assert c.post('/api/movil/logout/').status_code == 204
    assert c.get('/api/movil/me/').status_code == 401
    device.refresh_from_db()
    assert not device.activo

def test_expired_session(data):
    c,_,_,_,s,_,_ = data
    s.expira_en=timezone.now()-timedelta(seconds=1);s.save()
    assert c.get('/api/movil/me/').status_code == 401

def test_attendance_is_idempotent_and_separate(data):
    c,_,_,t,_,_,_ = data
    url=f'/api/movil/turnos/{t.pk}/asistencia/'
    r=c.post(url);assert r.status_code==200,r.data
    t.refresh_from_db();first=t.asistencia_confirmada_en
    assert first and t.estado=='CONFIRMADO'
    assert c.post(url).status_code==200
    t.refresh_from_db();assert first==t.asistencia_confirmada_en
    t.fecha_hora_inicio+=timedelta(days=1);t.fecha_hora_fin+=timedelta(days=1);t.save()
    t.refresh_from_db();assert t.asistencia_confirmada_en is None

def test_other_patient_and_doctor_cannot_answer(data):
    c,u,d,t,s,_,_=data
    other=get_user_model().objects.create_user(username='other',rol='paciente')
    Paciente.objects.create(user=other,nombre='Otro',apellido='Paciente',dni='MOB-2')
    s.user=other;s.save()
    assert c.get(f'/api/movil/turnos/{t.pk}/').status_code==404
    assert c.post(f'/api/movil/turnos/{t.pk}/asistencia/').status_code==404
    s.user=d;s.save()
    assert c.get(f'/api/movil/turnos/{t.pk}/').status_code==200
    assert c.post(f'/api/movil/turnos/{t.pk}/asistencia/').status_code==403
    d.is_staff=True;d.save()
    t.medico=Medico.objects.create(nombre='Otro',apellido='Doctor',matricula='MOB-2');t.save()
    assert c.get(f'/api/movil/turnos/{t.pk}/').status_code==404

@pytest.mark.parametrize('rol',['admin','enfermeria'])
def test_login_rejects_other_roles(rol):
    cache.clear()
    get_user_model().objects.create_user(username='role',password='test-password',rol=rol)
    assert APIClient().post('/api/movil/login/',{'username':'role','password':'test-password'}).status_code in (401,403)

@pytest.mark.parametrize('rol',['secretaria','secretaria_lab','laboratorio','bioquimico'])
def test_login_accepts_staff_clinical_roles(rol):
    cache.clear()
    get_user_model().objects.create_user(username=f'ok-{rol}',password='test-password',rol=rol)
    r = APIClient().post('/api/movil/login/',{'username':f'ok-{rol}','password':'test-password'},format='json')
    assert r.status_code == 200, r.data
    assert r.data['user']['rol'] == rol
    # Informes LIMS: ambas secretarías + lab/bio.
    assert r.data['user']['puede_informes'] is True

def test_push_registration_reports_service_disabled(data,settings):
    settings.MOBILE_PUSH_ENABLED=False
    c,*_=data
    r=c.post('/api/movil/push/',{'token':'ExpoPushToken[valid]','plataforma':'ios'},format='json')
    assert r.status_code==200 and not r.data['servicio_activo']
    assert c.post('/api/movil/push/',{'token':'https://untrusted','plataforma':'ios'},format='json').status_code==400

def test_reminder_deduplicated_and_private(data,settings):
    settings.MOBILE_PUSH_ENABLED=True
    _,_,_,t,_,_,_=data
    assert preparar_recordatorios()==1
    assert preparar_recordatorios()==0
    with patch('movil.recordatorios.requests.post',return_value=Mock(json=lambda:{'data':{'status':'ok','id':'ticket'}})) as send:
        assert enviar_pendientes()==1
        assert enviar_pendientes()==0
        payload=send.call_args.kwargs['json']
        assert payload['title']==f'SYNESIS movil · {settings.MOBILE_INSTITUTION_NAME}'
        assert payload['data']=={
            'turno_id': t.pk,
            'institucion': settings.MOBILE_INSTITUTION_CODE,
            'tipo': 'asistencia',
        }
        assert 'Privado' not in str(payload)
    t.refresh_from_db();assert t.estado=='CONFIRMADO'

@pytest.mark.parametrize('change',['cancel','attendance','reschedule','logout'])
def test_stale_reminders_never_sent(data,settings,change):
    settings.MOBILE_PUSH_ENABLED=True
    c,_,_,t,s,_,_=data
    preparar_recordatorios()
    if change=='cancel':t.estado='CANCELADO';t.save()
    elif change=='attendance':c.post(f'/api/movil/turnos/{t.pk}/asistencia/')
    elif change=='reschedule':
        t.fecha_hora_inicio+=timedelta(days=1);t.fecha_hora_fin+=timedelta(days=1);t.save()
    else:s.revocada=True;s.save()
    with patch('movil.recordatorios.requests.post') as send:
        assert enviar_pendientes()==0
        send.assert_not_called()
    assert RecordatorioTurno.objects.get().estado=='OMITIDO'

def test_disabled_no_network(data,settings):
    settings.MOBILE_PUSH_ENABLED=False
    preparar_recordatorios()
    with patch('movil.recordatorios.requests.post') as send:
        assert enviar_pendientes()==0;send.assert_not_called()

def test_invalid_device_deactivated(data,settings):
    settings.MOBILE_PUSH_ENABLED=True
    preparar_recordatorios()
    with patch('movil.recordatorios.requests.post',return_value=Mock(json=lambda:{'data':{'status':'error','details':{'error':'DeviceNotRegistered'}}})):
        assert enviar_pendientes()==0
    data[5].refresh_from_db();assert not data[5].activo

def test_mobile_booking_asistencia_and_no_cancel_paciente(data):
    from datetime import datetime, time
    from medicos.models import DisponibilidadMedico
    c,_,_,t,_,_,_=data
    # Liberar el turno del fixture para poder reservar otro desde la app.
    t.estado = 'CANCELADO'
    t.save(update_fields=['estado'])
    day=timezone.localdate()+timedelta(days=7)
    start=timezone.make_aware(datetime.combine(day,time(9)))
    from turnos.models import Recurso
    cons=Recurso.objects.create(nombre='Cons movil',ubicacion='CEHTA',tipo_recurso='CONSULTORIO',activo=True)
    h=DisponibilidadMedico.objects.create(medico=t.medico,dia_semana=day.weekday(),hora_inicio=time(9),hora_fin=time(13),tipo='CONSULTA',recurso=cons,activo=True)
    r=c.post('/api/movil/turnos/reservar-horario/',{'horario_id':h.pk,'inicio':start.isoformat()},format='json')
    assert r.status_code==201,r.data
    pk=r.data['id']
    assert r.data['estado']=='RESERVADO'
    assert r.data.get('puede_reprogramar') is True
    assert r.data.get('puede_cancelar') is False
    assert 'prioridad' not in r.data and 'recurso' not in r.data
    assert c.post(f'/api/movil/turnos/{pk}/confirmar/').status_code==200
    assert Turno.objects.get(pk=pk).estado=='CONFIRMADO'
    assert c.post(f'/api/movil/turnos/{pk}/asistencia/').status_code==200
    # Cancelar normal: paciente no puede (403). Reprogramar ≥48 h: sí.
    assert c.post(f'/api/movil/turnos/{pk}/cancelar/',{'motivo':'No puedo asistir'},format='json').status_code==403
    r=c.post(
        f'/api/movil/turnos/{pk}/reprogramar-horario/',
        {
            'horario_id': h.pk,
            'inicio': (start + timedelta(minutes=20)).isoformat(),
            'motivo': 'Cambio de horario',
        },
        format='json',
    )
    assert r.status_code == 200, r.data
    nuevo = Turno.objects.get(pk=r.data['id'])
    assert nuevo.reprogramaciones_paciente == 1
    assert nuevo.estado == 'CONFIRMADO'
    assert nuevo.requiere_aceptacion_paciente is False
    # Segunda reprogramación: bloqueada.
    r2 = c.post(
        f'/api/movil/turnos/{nuevo.pk}/reprogramar-horario/',
        {
            'horario_id': h.pk,
            'inicio': (start + timedelta(minutes=40)).isoformat(),
            'motivo': 'Otro cambio',
        },
        format='json',
    )
    assert r2.status_code in (400, 403)
    updated = Turno.objects.get(pk=pk)
    assert updated.estado == 'CANCELADO'

def test_transient_push_error_retries_later(data,settings):
    import requests
    settings.MOBILE_PUSH_ENABLED=True
    preparar_recordatorios()
    with patch('movil.recordatorios.requests.post',side_effect=requests.Timeout):
        assert enviar_pendientes()==0
    r=RecordatorioTurno.objects.get()
    assert r.estado=='PENDIENTE' and r.intentos==1 and r.proximo_intento>timezone.now()

def test_future_outside_window_not_prepared(data):
    """Fuera de la ventana de ~48 hs (+ margen finde): no preparar asistencia."""
    t = data[3]
    t.fecha_hora_inicio = timezone.now() + timedelta(days=6)
    t.fecha_hora_fin = t.fecha_hora_inicio + timedelta(minutes=20)
    t.save(update_fields=['fecha_hora_inicio', 'fecha_hora_fin', 'updated_at'])
    assert preparar_recordatorios() == 0

def test_public_institution_identity(settings, monkeypatch):
    settings.MOBILE_INSTITUTION_CODE='CLINICA-B'
    settings.MOBILE_INSTITUTION_NAME='Clínica B'
    monkeypatch.setenv('EMR_KIOSCO_LAN_ORIGIN', 'http://192.168.1.94:3000')
    r=APIClient().get('/api/movil/institucion/')
    assert r.status_code==200
    assert r.data['code']=='CLINICA-B'
    assert r.data['name']=='Clínica B'
    assert r.data['kiosco_anuncio_url']=='http://192.168.1.94:3000/kiosco-recepcion'
    settings.MOBILE_INSTITUTION_CODE=''
    assert APIClient().get('/api/movil/institucion/').status_code==503

def test_llamado_activo_polling(data):
    from recepcion.models import LlegadaRecepcion, PuestoRecepcion
    c, u, _d, t, *_ = data
    assert c.get('/api/movil/llamado-activo/').data['activo'] is False
    puesto, _ = PuestoRecepcion.objects.get_or_create(
        codigo='test-puesto',
        defaults={'nombre': 'Puesto test', 'activo': True, 'orden': 1},
    )
    LlegadaRecepcion.objects.create(
        paciente=t.paciente,
        puesto=puesto,
        turno=t,
        tipo_actividad='CONSULTA',
        estado_flujo='LLAMADO',
        fecha=timezone.localdate(),
        checkin_en=timezone.now(),
        llamado_en=timezone.now(),
        destino_label='Consultorio 1',
        numero_orden_dia=1,
    )
    r = c.get('/api/movil/llamado-activo/')
    assert r.status_code == 200
    assert r.data['activo'] is True
    assert r.data['destino'] == 'Consultorio 1'
    assert r.data['tipo'] == 'llamado_medico'


def test_reserva_hoy_nace_confirmado(data):
    from datetime import datetime, time
    from medicos.models import DisponibilidadMedico
    from turnos.models import Recurso
    c,_,_,t,_,_,_=data
    t.estado='CANCELADO';t.save(update_fields=['estado'])
    cons=Recurso.objects.create(nombre='Cons hoy',ubicacion='CEHTA',tipo_recurso='CONSULTORIO',activo=True)
    # Mañana 10:00 → sigue CONFIRMADO (regla hoy/mañana) y evita carrera con la hora actual.
    day = timezone.localdate() + timedelta(days=1)
    start = timezone.make_aware(datetime.combine(day, time(10, 0)))
    h=DisponibilidadMedico.objects.create(
        medico=t.medico,dia_semana=day.weekday(),
        hora_inicio=time(9, 0),hora_fin=time(13, 0),
        tipo='CONSULTA',recurso=cons,activo=True,
    )
    r=c.post('/api/movil/turnos/reservar-horario/',{'horario_id':h.pk,'inicio':start.isoformat()},format='json')
    assert r.status_code==201,r.data
    assert r.data['estado']=='CONFIRMADO'


def test_push_confirmacion_turno_lejos(data,settings):
    from movil.recordatorios import preparar_recordatorios_confirmacion
    settings.MOBILE_PUSH_ENABLED=True
    _,_,_,t,_,_,_=data
    t.estado='RESERVADO'
    t.fecha_hora_inicio=timezone.now()+timedelta(days=5)
    t.fecha_hora_fin=t.fecha_hora_inicio+timedelta(minutes=20)
    t.save()
    assert preparar_recordatorios_confirmacion()==1
    with patch('movil.recordatorios.requests.post',return_value=Mock(json=lambda:{'data':{'status':'ok','id':'ticket-c'}})) as send:
        assert enviar_pendientes()==1
        assert send.call_args.kwargs['json']['data']['tipo']=='confirmar_turno'


def test_estoy_en_sala_y_lab(data):
    from recepcion.models import PuestoRecepcion
    from recepcion.services import CODIGO_PUESTO_1, CODIGO_SALA_EXTRACCION
    c,_,_,t,_,_,_=data
    PuestoRecepcion.objects.get_or_create(
        codigo=CODIGO_PUESTO_1,
        defaults={'nombre':'Puesto 1','etiqueta_paciente':'Puesto 1','activo':True,'orden':1},
    )
    PuestoRecepcion.objects.get_or_create(
        codigo=CODIGO_SALA_EXTRACCION,
        defaults={'nombre':'Sala extracción','etiqueta_paciente':'Sala de extracción','activo':True,'orden':99},
    )
    # Turno del fixture no es hoy → no puedo estoy en sala.
    hoy = c.get('/api/movil/recepcion/hoy/')
    assert hoy.status_code==200
    assert hoy.data['puedo_estoy_en_sala'] is False
    # Hoy pero fuera de la ventana (faltan 2 h) → no.
    start = timezone.now()+timedelta(hours=2)
    t.fecha_hora_inicio=start
    t.fecha_hora_fin=start+timedelta(minutes=20)
    t.estado='CONFIRMADO'
    t.save()
    hoy = c.get('/api/movil/recepcion/hoy/')
    assert hoy.data['puedo_estoy_en_sala'] is False
    assert c.post('/api/movil/recepcion/estoy-en-sala/',{},format='json').status_code==400
    # Dentro de la ventana (faltan 30 min) → sí.
    start = timezone.now()+timedelta(minutes=30)
    t.fecha_hora_inicio=start
    t.fecha_hora_fin=start+timedelta(minutes=20)
    t.save()
    hoy = c.get('/api/movil/recepcion/hoy/')
    assert hoy.data['puedo_estoy_en_sala'] is True
    assert any(
        x['turno_id']==t.pk and x['puedo_estoy_en_sala']
        for x in hoy.data.get('turnos_estoy_en_sala') or []
    )
    r = c.post('/api/movil/recepcion/estoy-en-sala/',{'turno_id': t.pk},format='json')
    assert r.status_code==200,r.data
    assert r.data['codigo_llamado']
    hoy2 = c.get('/api/movil/recepcion/hoy/')
    assert hoy2.data['puedo_estoy_en_sala'] is False
    assert hoy2.data['estoy_en_sala']['codigo_llamado']==r.data['codigo_llamado']
    lab = c.post('/api/movil/recepcion/anuncio-lab/',{},format='json')
    assert lab.status_code==200,lab.data
    assert (lab.data.get('codigo_llamado') or '').startswith('L')


def test_estoy_en_sala_rechaza_si_ya_paso_inicio(data):
    from recepcion.models import PuestoRecepcion
    from recepcion.services import CODIGO_PUESTO_1
    c,_,_,t,_,_,_=data
    PuestoRecepcion.objects.get_or_create(
        codigo=CODIGO_PUESTO_1,
        defaults={'nombre':'Puesto 1','etiqueta_paciente':'Puesto 1','activo':True,'orden':1},
    )
    start = timezone.now()-timedelta(minutes=5)
    t.fecha_hora_inicio=start
    t.fecha_hora_fin=start+timedelta(minutes=20)
    t.estado='CONFIRMADO'
    t.save()
    hoy = c.get('/api/movil/recepcion/hoy/')
    assert hoy.status_code==200
    assert hoy.data['puedo_estoy_en_sala'] is False
    r = c.post('/api/movil/recepcion/estoy-en-sala/',{'turno_id': t.pk},format='json')
    assert r.status_code==400


def test_estoy_en_sala_estudio_en_ventana(data):
    """Misma ventana de 1 h para turnos de estudio (tipo_actividad ESTUDIO)."""
    from turnos.models import Recurso
    from recepcion.models import PuestoRecepcion
    from recepcion.services import CODIGO_PUESTO_1
    c,u,_,_,_,_,_=data
    PuestoRecepcion.objects.get_or_create(
        codigo=CODIGO_PUESTO_1,
        defaults={'nombre':'Puesto 1','etiqueta_paciente':'Puesto 1','activo':True,'orden':1},
    )
    pac = Paciente.objects.get(user=u)
    med = Medico.objects.first()
    sala = Recurso.objects.create(
        nombre='Sala estudio móvil',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
        activo=True,
    )
    start = timezone.now()+timedelta(minutes=20)
    te = Turno.objects.create(
        paciente=pac,
        medico=med,
        recurso=sala,
        fecha_hora_inicio=start,
        fecha_hora_fin=start+timedelta(minutes=30),
        estado='CONFIRMADO',
        motivo_reserva='Estudio: Eco',
    )
    hoy = c.get('/api/movil/recepcion/hoy/')
    assert hoy.status_code==200
    assert hoy.data['puedo_estoy_en_sala'] is True
    item = next(x for x in hoy.data['turnos_estoy_en_sala'] if x['turno_id']==te.pk)
    assert item['tipo_actividad'] in ('ESTUDIO', 'PROCEDIMIENTO')
    assert item['puedo_estoy_en_sala'] is True
    r = c.post('/api/movil/recepcion/estoy-en-sala/',{'turno_id': te.pk},format='json')
    assert r.status_code==200,r.data
    assert r.data['tipo_actividad']=='ESTUDIO'
