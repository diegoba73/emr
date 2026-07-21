"""Tests de invariantes de contexto en Atencion (ambulatoria vs internación)."""
import pytest
from django.core.exceptions import ValidationError

from internacion.models import Sector, Cama, Internacion
from internacion.tests.helpers import unique_suffix
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno


@pytest.fixture
def medico(db):
    esp, _ = Especialidad.objects.get_or_create(nombre='Cardiología ctx')
    return Medico.objects.create(
        matricula=f'M-CTX-{unique_suffix()}',
        nombre='Ana',
        apellido='Ruiz',
        especialidad=esp,
    )


@pytest.fixture
def paciente(db):
    suffix = unique_suffix()
    return Paciente.objects.create(
        dni=f'CTX-{suffix}',
        nombre='Luis',
        apellido='Díaz',
    )


@pytest.fixture
def internacion(db, paciente, medico):
    sector = Sector.objects.create(nombre=f'UCO-ctx-{unique_suffix()}')
    cama = Cama.objects.create(
        nombre=f'C1-{unique_suffix()}',
        sector=sector,
        estado='DISPONIBLE',
    )
    return Internacion.objects.create(
        paciente=paciente,
        cama=cama,
        medico=medico,
        diagnostico_ingreso='IAM',
        activo=True,
    )


@pytest.mark.django_db
def test_atencion_ambulatoria_no_permite_internacion(paciente, medico):
    recurso = Recurso.objects.create(
        nombre=f'Cons-ctx-{unique_suffix()}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
    )
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio='2026-01-10T10:00:00Z',
        estado=Turno.Estado.CONFIRMADO,
    )
    sector = Sector.objects.create(nombre=f'UCO-inv-{unique_suffix()}')
    cama = Cama.objects.create(
        nombre=f'C2-{unique_suffix()}',
        sector=sector,
        estado='DISPONIBLE',
    )
    internacion = Internacion.objects.create(
        paciente=paciente,
        cama=cama,
        medico=medico,
        diagnostico_ingreso='Dx',
        activo=True,
    )
    atencion = Atencion(
        turno=turno,
        paciente=paciente,
        medico_principal=medico,
        contexto_atencion=Atencion.ContextoAtencion.AMBULATORIA,
        internacion=internacion,
        tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
    )
    with pytest.raises(ValidationError):
        atencion.full_clean()


@pytest.mark.django_db
def test_atencion_internacion_requiere_internacion_y_prohibe_turno(paciente, medico, internacion):
    atencion = Atencion(
        paciente=paciente,
        medico_principal=medico,
        contexto_atencion=Atencion.ContextoAtencion.INTERNACION,
        tipo_atencion=Atencion.TIPO_ATENCION_INTERNACION,
    )
    with pytest.raises(ValidationError):
        atencion.full_clean()

    recurso = Recurso.objects.create(
        nombre=f'Cons-int-{unique_suffix()}',
        ubicacion=Recurso.Ubicacion.CEHTA,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
    )
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio='2026-01-10T10:00:00Z',
        estado=Turno.Estado.CONFIRMADO,
    )
    atencion = Atencion(
        turno=turno,
        paciente=paciente,
        medico_principal=medico,
        contexto_atencion=Atencion.ContextoAtencion.INTERNACION,
        internacion=internacion,
        tipo_atencion=Atencion.TIPO_ATENCION_INTERNACION,
    )
    with pytest.raises(ValidationError):
        atencion.full_clean()


@pytest.mark.django_db
def test_atencion_internacion_paciente_debe_coincidir(paciente, medico, internacion):
    otro = Paciente.objects.create(dni=f'OTR-{unique_suffix()}', nombre='Otro', apellido='Px')
    atencion = Atencion(
        paciente=otro,
        medico_principal=medico,
        contexto_atencion=Atencion.ContextoAtencion.INTERNACION,
        internacion=internacion,
        tipo_atencion=Atencion.TIPO_ATENCION_INTERNACION,
    )
    with pytest.raises(ValidationError):
        atencion.full_clean()
