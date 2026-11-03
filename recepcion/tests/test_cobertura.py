"""Cobertura dinámica de recepción: filtrado, llamar y L sin cobertura de secretaría."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from pacientes.models import Paciente
from recepcion import services
from recepcion.models import PuestoRecepcion

User = get_user_model()


@pytest.fixture
def puestos(db):
    def _ensure(codigo, **defaults):
        obj, created = PuestoRecepcion.objects.get_or_create(codigo=codigo, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(obj, k, v)
            obj.save()
        return obj

    p1 = _ensure(
        'puesto-1',
        nombre='Puesto 1',
        etiqueta_paciente='Puesto 1',
        modo='TODO',
        activo=True,
        es_fallback=True,
        orden=1,
    )
    p2 = _ensure(
        'puesto-2',
        nombre='Puesto 2',
        etiqueta_paciente='Puesto 2',
        modo='TODO',
        activo=True,
        es_fallback=False,
        orden=2,
    )
    sala = _ensure(
        'sala-extraccion',
        nombre='Sala de extracción',
        etiqueta_paciente='Sala de extracción',
        modo='REGLAS',
        activo=True,
        es_fallback=False,
        orden=10,
    )
    # Solo p1 como fallback para placeholder predecible.
    PuestoRecepcion.objects.exclude(pk=p1.pk).update(es_fallback=False)
    p1.es_fallback = True
    p1.save(update_fields=['es_fallback'])
    return p1, p2, sala


@pytest.fixture
def secretaria(db):
    return User.objects.create_user(username='sec_cov', password='x', rol='secretaria')


@pytest.fixture
def secretaria2(db):
    return User.objects.create_user(username='sec_cov2', password='x', rol='secretaria')


@pytest.fixture
def paciente(db):
    return Paciente.objects.create(nombre='Ana', apellido='Perez', dni='40111222')


@pytest.mark.django_db
def test_llamar_sin_cobertura_falla(puestos, secretaria, paciente):
    llegada = services.checkin_walkin(
        paciente=paciente, tipo_actividad='SIN_TURNO', motivo='SIN_TURNO'
    )
    with pytest.raises(ValidationError) as exc:
        services.llamar_paciente(llegada, user=secretaria)
    assert 'cobertura' in str(exc.value).lower()


@pytest.mark.django_db
def test_llamar_setea_puesto_de_cobertura(puestos, secretaria, paciente):
    p1, p2, _sala = puestos
    services.guardar_cobertura_hoy(
        usuario=secretaria,
        puesto_id=p2.id,
        tipos=['SIN_TURNO', 'CONSULTA'],
    )
    llegada = services.checkin_walkin(
        paciente=paciente, tipo_actividad='SIN_TURNO', motivo='SIN_TURNO'
    )
    assert llegada.puesto_id == p1.id  # placeholder (fallback)
    llegada = services.llamar_paciente(llegada, user=secretaria)
    assert llegada.estado_flujo == 'LLAMADO'
    assert llegada.puesto_id == p2.id
    assert llegada.destino_label == 'Puesto 2'
    assert llegada.zona_llamado == 'RECEPCION'


@pytest.mark.django_db
def test_llamar_tipo_fuera_de_cobertura_falla(puestos, secretaria, paciente):
    p1, _p2, _sala = puestos
    services.guardar_cobertura_hoy(
        usuario=secretaria,
        puesto_id=p1.id,
        tipos=['CONSULTA'],
    )
    llegada = services.checkin_walkin(
        paciente=paciente, tipo_actividad='ESTUDIO', motivo='ESTUDIO'
    )
    with pytest.raises(ValidationError):
        services.llamar_paciente(llegada, user=secretaria)


@pytest.mark.django_db
def test_extraccion_no_usa_cobertura_secretaria(puestos, secretaria, paciente):
    p1, _p2, sala = puestos
    services.guardar_cobertura_hoy(
        usuario=secretaria,
        puesto_id=p1.id,
        tipos=['CONSULTA', 'SIN_TURNO'],
    )
    llegada = services.checkin_walkin(
        paciente=paciente, tipo_actividad='EXTRACCION', motivo='EXTRACCION'
    )
    # Lab llama sin cobertura de secretaría (user=None o lab): destino sala.
    llegada = services.llamar_paciente(llegada, user=None)
    assert llegada.puesto_id == sala.id
    assert 'extracción' in (llegada.destino_label or '').lower() or llegada.destino_label == sala.label_publico


@pytest.mark.django_db
def test_medico_llamar_no_pide_cobertura(puestos, paciente):
    """Médico llama tras check-in: destino consultorio, sin cobertura de secretaría."""
    from datetime import timedelta

    from medicos.models import Medico
    from turnos.models import Recurso, Turno
    from recepcion.models import LlegadaRecepcion

    p1, _p2, _sala = puestos
    medico_user = User.objects.create_user(username='med_cov', password='x', rol='medico')
    medico = Medico.objects.create(
        user=medico_user,
        nombre='Roberto',
        apellido='Ingaramo',
        matricula=f'M-COV-{medico_user.pk}',
    )
    recurso = Recurso.objects.create(
        nombre='Consultorio Test Cov',
        tipo_recurso='CONSULTORIO',
        activo=True,
    )
    ahora = timezone.now()
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=ahora,
        fecha_hora_fin=ahora + timedelta(minutes=20),
        estado='CONFIRMADO',
    )
    llegada = LlegadaRecepcion.objects.create(
        paciente=paciente,
        puesto=p1,
        turno=turno,
        tipo_actividad='CONSULTA',
        estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
        fecha=timezone.localdate(),
        checkin_en=ahora,
        destino_recurso=recurso,
        destino_label=recurso.nombre,
        codigo_llamado='T99',
        prefijo_llamado='T',
    )
    llamada = services.llamar_paciente(llegada, user=medico_user)
    assert llamada.zona_llamado == 'MEDICO'
    assert llamada.destino_label == 'Consultorio Test Cov'
    assert llamada.estado_flujo == 'LLAMADO'


@pytest.mark.django_db
def test_api_cobertura_hoy_y_tablero_filtra(puestos, secretaria, secretaria2, paciente):
    p1, p2, _sala = puestos
    client = APIClient()
    client.force_authenticate(user=secretaria)

    r = client.get('/api/recepcion/cobertura-hoy/')
    assert r.status_code == 200
    assert r.data['cobertura'] is None

    r = client.put(
        '/api/recepcion/cobertura-hoy/',
        {'puesto': p1.id, 'tipos': ['CONSULTA', 'SIN_TURNO']},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['puesto'] == p1.id
    assert 'CONSULTA' in r.data['tipos']

    # Llegadas: S visible para sec1; E no (en espera recepción).
    services.checkin_walkin(paciente=paciente, tipo_actividad='SIN_TURNO', motivo='SIN_TURNO')
    pac_e = Paciente.objects.create(nombre='Eva', apellido='Diaz', dni='40111223')
    services.checkin_walkin(paciente=pac_e, tipo_actividad='ESTUDIO', motivo='ESTUDIO')

    r = client.get('/api/recepcion/llegadas/tablero/')
    assert r.status_code == 200
    tipos = {x['tipo_actividad'] for x in r.data['llegadas']}
    assert 'SIN_TURNO' in tipos
    assert 'ESTUDIO' not in tipos

    # Segunda secretaria con E+P ve estudio.
    services.guardar_cobertura_hoy(
        usuario=secretaria2,
        puesto_id=p2.id,
        tipos=['ESTUDIO', 'PROCEDIMIENTO'],
    )
    client2 = APIClient()
    client2.force_authenticate(user=secretaria2)
    r2 = client2.get('/api/recepcion/llegadas/tablero/')
    tipos2 = {x['tipo_actividad'] for x in r2.data['llegadas']}
    assert 'ESTUDIO' in tipos2
    assert 'SIN_TURNO' not in tipos2
