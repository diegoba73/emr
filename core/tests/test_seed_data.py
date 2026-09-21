"""El seed puede repetirse sin reemplazar situaciones clínicas existentes."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.management.commands.seed_data import QA_LIMS_NUMERO, QA_MUESTRA_CODIGO, QA_TURNO_MOTIVO
from internacion.models import Cama, Internacion, Sector
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno
from usuarios.models import User


def seed():
    output = StringIO()
    call_command('seed_data', stdout=output)
    return output.getvalue()


def assert_lims_demo():
    solicitud = SolicitudExamen.objects.get(numero=QA_LIMS_NUMERO)
    assert ResultadoExamen.objects.filter(solicitud=solicitud).count() == 1
    assert Muestra.objects.filter(codigo_barra=QA_MUESTRA_CODIGO, solicitud=solicitud).count() == 1


@pytest.fixture
def paciente_demo(db):
    user = User.objects.create_user(username='paciente1', rol='paciente')
    return Paciente.objects.create(user=user, dni='QA-SEED-PREEXISTENTE',
                                   nombre='Paciente Demo', apellido='Uno')


@pytest.fixture
def medico_preexistente(db):
    return Medico.objects.create(matricula='QA-SEED-MEDICO', nombre='Medico', apellido='Previo')


@pytest.mark.django_db
@pytest.mark.parametrize('contexto', [Atencion.ContextoAtencion.AMBULATORIA, Atencion.ContextoAtencion.GUARDIA])
@pytest.mark.parametrize('estado', [Atencion.EstadoClinico.ABIERTA, Atencion.EstadoClinico.EN_REVISION])
def test_seed_con_atencion_previa_conserva_sus_datos_y_continua_lims(paciente_demo, medico_preexistente, contexto, estado):
    recurso = Recurso.objects.create(nombre='Consultorio previo', ubicacion=Recurso.Ubicacion.CEHTA,
                                     tipo_recurso=Recurso.TipoRecurso.CONSULTORIO)
    inicio = timezone.now() - timedelta(days=1)
    turno = Turno.objects.create(paciente=paciente_demo, medico=medico_preexistente, recurso=recurso,
                                 fecha_hora_inicio=inicio, fecha_hora_fin=inicio + timedelta(minutes=30),
                                 estado=Turno.Estado.REALIZADO, motivo_reserva='Encuentro previo')
    atencion = Atencion.objects.create(
        paciente=paciente_demo, medico_principal=medico_preexistente, turno=turno,
        contexto_atencion=contexto, estado_clinico=estado,
        tipo_atencion=Recurso.TipoRecurso.CONSULTORIO, observaciones_generales='Conservar este encuentro',
    )
    antes = Atencion.objects.filter(pk=atencion.pk).values().get()
    turno_antes = Turno.objects.filter(pk=turno.pk).values().get()
    for _ in range(2):
        output = seed()
        assert 'Se conserva la situación clínica activa' in output
        assert Atencion.objects.filter(paciente=paciente_demo).count() == 1
        assert Atencion.objects.filter(pk=atencion.pk).values().get() == antes
        assert Turno.objects.filter(pk=turno.pk).values().get() == turno_antes
        demo = Turno.objects.get(motivo_reserva=QA_TURNO_MOTIVO)
        assert not Atencion.objects.filter(turno=demo).exists()
        assert_lims_demo()


@pytest.mark.django_db
def test_seed_con_paciente_internado_no_modifica_internacion(paciente_demo, medico_preexistente):
    sector = Sector.objects.create(nombre='Sector seed')
    cama = Cama.objects.create(nombre='Cama seed', sector=sector)
    ingreso = Internacion.objects.create(paciente=paciente_demo, medico=medico_preexistente, cama=cama)
    antes = Internacion.objects.filter(pk=ingreso.pk).values().get()
    for _ in range(2):
        assert 'Se conserva la situación clínica activa' in seed()
        assert not Atencion.objects.filter(paciente=paciente_demo).exists()
        assert Internacion.objects.filter(pk=ingreso.pk).values().get() == antes
        cama.refresh_from_db()
        assert cama.estado == 'OCUPADA'
        assert_lims_demo()


@pytest.mark.django_db
def test_seed_nuevo_es_idempotente_y_conserva_atencion_demo_finalizada():
    seed()
    turno = Turno.objects.get(motivo_reserva=QA_TURNO_MOTIVO)
    atencion = Atencion.objects.get(turno=turno)
    antes = Atencion.objects.filter(pk=atencion.pk).values().get()
    seed()
    assert Atencion.objects.filter(paciente=atencion.paciente).count() == 1
    assert Atencion.objects.filter(pk=atencion.pk).values().get() == antes
    assert_lims_demo()
    atencion.estado_clinico = Atencion.EstadoClinico.FINALIZADA
    atencion.fecha_cierre = timezone.now()
    atencion.save()
    finalizada = Atencion.objects.filter(pk=atencion.pk).values().get()
    seed()
    assert Atencion.objects.filter(pk=atencion.pk).values().get() == finalizada
    assert Atencion.objects.filter(paciente=atencion.paciente).count() == 1
