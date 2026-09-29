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
    U = get_user_model()
    u = U.objects.create_user(username='mobilepatient', password='test-password', rol='paciente')
    p = Paciente.objects.create(user=u, nombre='Paciente', apellido='Privado', dni='MOB-1')
    d = U.objects.create_user(username='mobiledoc', password='test-password', rol='medico')
    m = Medico.objects.create(user=d, nombre='Medico', apellido='Uno', matricula='MOB-1')
    start = timezone.now() + timedelta(hours=23)
    t = Turno.objects.create(paciente=p, medico=m, fecha_hora_inicio=start,
        fecha_hora_fin=start+timedelta(minutes=20), estado='RESERVADO')
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
    assert first and t.estado=='RESERVADO'
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

@pytest.mark.parametrize('rol',['secretaria','admin','enfermeria'])
def test_login_rejects_other_roles(rol):
    cache.clear()
    get_user_model().objects.create_user(username='role',password='test-password',rol=rol)
    assert APIClient().post('/api/movil/login/',{'username':'role','password':'test-password'}).status_code in (401,403)

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
        assert payload['data']=={'turno_id':t.pk,'institucion':settings.MOBILE_INSTITUTION_CODE}
        assert 'Privado' not in str(payload)
    t.refresh_from_db();assert t.estado=='RESERVADO'

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

def test_mobile_booking_and_reschedule(data):
    from datetime import datetime, time
    from medicos.models import DisponibilidadMedico
    c,_,_,t,_,_,_=data
    day=timezone.localdate()+timedelta(days=7)
    start=timezone.make_aware(datetime.combine(day,time(9)))
    h=DisponibilidadMedico.objects.create(medico=t.medico,dia_semana=day.weekday(),hora_inicio=time(9),hora_fin=time(13))
    r=c.post('/api/movil/turnos/reservar-horario/',{'horario_id':h.pk,'inicio':start.isoformat()},format='json')
    assert r.status_code==201,r.data
    pk=r.data['id']
    assert 'prioridad' not in r.data and 'recurso' not in r.data
    assert c.post(f'/api/movil/turnos/{pk}/asistencia/').status_code==200
    r=c.post(f'/api/movil/turnos/{pk}/reprogramar-horario/',{'horario_id':h.pk,'inicio':(start+timedelta(minutes=20)).isoformat(),'motivo':'Cambio de horario'},format='json')
    assert r.status_code==200,r.data
    updated=Turno.objects.get(pk=pk)
    assert updated.asistencia_confirmada_en is None
    assert updated.fecha_hora_inicio==start+timedelta(minutes=20)
    assert c.post(f'/api/movil/turnos/{pk}/cancelar/',{'motivo':'No puedo asistir'},format='json').status_code==200

def test_transient_push_error_retries_later(data,settings):
    import requests
    settings.MOBILE_PUSH_ENABLED=True
    preparar_recordatorios()
    with patch('movil.recordatorios.requests.post',side_effect=requests.Timeout):
        assert enviar_pendientes()==0
    r=RecordatorioTurno.objects.get()
    assert r.estado=='PENDIENTE' and r.intentos==1 and r.proximo_intento>timezone.now()

def test_future_outside_window_not_prepared(data):
    t=data[3]
    t.fecha_hora_inicio+=timedelta(hours=2);t.fecha_hora_fin+=timedelta(hours=2);t.save()
    assert preparar_recordatorios()==0

def test_public_institution_identity(settings):
    settings.MOBILE_INSTITUTION_CODE='CLINICA-B'
    settings.MOBILE_INSTITUTION_NAME='Clínica B'
    r=APIClient().get('/api/movil/institucion/')
    assert r.status_code==200
    assert r.data=={'code':'CLINICA-B','name':'Clínica B'}
    settings.MOBILE_INSTITUTION_CODE=''
    assert APIClient().get('/api/movil/institucion/').status_code==503
