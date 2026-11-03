import pytest
from django.utils import timezone

from pacientes.models import Paciente
from recepcion.models import LlegadaRecepcion, PuestoRecepcion
from recepcion import services


@pytest.fixture
def puesto(db):
    return PuestoRecepcion.objects.create(
        codigo='t-main',
        nombre='Puesto 1',
        modo='TODO',
        activo=True,
        es_fallback=True,
        orden=1,
    )


@pytest.fixture
def paciente(db):
    return Paciente.objects.create(nombre='Ana', apellido='Perez', dni='30111222')


@pytest.mark.django_db
def test_prefijos_y_secuencia_por_letra(puesto, paciente):
    hoy = timezone.localdate()
    a = services.checkin_walkin(paciente=paciente, tipo_actividad='SIN_TURNO', motivo='SIN_TURNO')
    assert a.prefijo_llamado == 'S'
    assert a.codigo_llamado == 'S01'
    assert a.estado_flujo == LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION

    pac2 = Paciente.objects.create(nombre='Luis', apellido='Gomez', dni='30111223')
    b = services.checkin_walkin(paciente=pac2, tipo_actividad='EXTRACCION', motivo='EXTRACCION')
    assert b.codigo_llamado == 'L01'

    pac3 = Paciente.objects.create(nombre='Eva', apellido='Diaz', dni='30111224')
    c = services.checkin_walkin(paciente=pac3, tipo_actividad='SIN_TURNO', motivo='SIN_TURNO')
    assert c.codigo_llamado == 'S02'


@pytest.mark.django_db
def test_extraccion_no_deriva_a_medico(puesto, paciente):
    llegada = services.checkin_walkin(
        paciente=paciente, tipo_actividad='EXTRACCION', motivo='EXTRACCION'
    )
    with pytest.raises(Exception):
        services.derivar_a_espera_clinica(llegada)


@pytest.mark.django_db
def test_ya_voy_recepcion_no_cambia_estado(puesto, paciente):
    """En llamado de ventanilla, «Ya voy» solo acusa en el celular; no marca EN_ATENCION/ATENDIDO."""
    llegada = services.checkin_walkin(
        paciente=paciente, tipo_actividad='SIN_TURNO', motivo='SIN_TURNO'
    )
    llegada = services.llamar_paciente(llegada)
    assert llegada.estado_flujo == 'LLAMADO'
    assert llegada.zona_llamado == 'RECEPCION'
    llegada = services.paciente_ya_voy(llegada)
    assert llegada.estado_flujo == 'LLAMADO'


@pytest.mark.django_db
def test_ya_voy_medico_pasa_a_en_atencion(puesto, paciente):
    from datetime import timedelta

    from django.contrib.auth import get_user_model
    from medicos.models import Medico
    from recepcion.models import LlegadaRecepcion
    from turnos.models import Recurso, Turno

    User = get_user_model()
    medico_user = User.objects.create_user(username='med_yavoy', password='x', rol='medico')
    medico = Medico.objects.create(
        user=medico_user,
        nombre='Ana',
        apellido='Med',
        matricula=f'M-YV-{medico_user.pk}',
    )
    recurso = Recurso.objects.create(nombre='Consultorio YaVoy', tipo_recurso='CONSULTORIO', activo=True)
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
        puesto=puesto,
        turno=turno,
        tipo_actividad='CONSULTA',
        estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
        fecha=timezone.localdate(),
        checkin_en=ahora,
        destino_recurso=recurso,
        destino_label=recurso.nombre,
    )
    llegada = services.llamar_paciente(llegada, user=medico_user)
    assert llegada.zona_llamado == 'MEDICO'
    llegada = services.paciente_ya_voy(llegada)
    assert llegada.estado_flujo == 'EN_ATENCION'
