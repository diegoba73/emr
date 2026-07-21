"""Tests de atenciones de guardia cardiológica."""
import pytest

from historias_clinicas.services import consulta_hc_id_para_atencion
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente
from turnos.models import Atencion, ConsultaAmbulatoria
from turnos.services import AtencionService, BusinessLogicError
from internacion.tests.helpers import unique_suffix


@pytest.fixture
def medico(db):
    esp, _ = Especialidad.objects.get_or_create(nombre=f'Cardio-guard-{unique_suffix()}')
    return Medico.objects.create(
        matricula=f'M-G-{unique_suffix()}',
        nombre='Pedro',
        apellido='Guardia',
        especialidad=esp,
    )


@pytest.fixture
def paciente(db):
    suffix = unique_suffix()
    return Paciente.objects.create(
        dni=f'G-{suffix}',
        nombre='María',
        apellido='Urgencia',
    )


@pytest.mark.django_db
def test_iniciar_atencion_guardia_crea_registros(paciente, medico):
    outcome = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
        motivo_consulta='Dolor torácico',
    )
    atencion = outcome.atencion
    assert outcome.created_new is True
    assert atencion.contexto_atencion == Atencion.ContextoAtencion.GUARDIA
    assert atencion.tipo_atencion == 'GUARDIA'
    assert ConsultaAmbulatoria.objects.filter(atencion=atencion).exists()
    assert consulta_hc_id_para_atencion(atencion) is not None


@pytest.mark.django_db
def test_atencion_guardia_no_permite_internacion(paciente, medico):
    outcome = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
    )
    from internacion.models import Sector, Cama, Internacion

    sector = Sector.objects.create(nombre=f'UCO-g-{unique_suffix()}')
    cama = Cama.objects.create(
        nombre=f'C-g-{unique_suffix()}',
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
    atencion = outcome.atencion
    atencion.internacion = internacion
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        atencion.full_clean()


@pytest.mark.django_db
def test_iniciar_guardia_paciente_inexistente(medico):
    with pytest.raises(BusinessLogicError):
        AtencionService.iniciar_atencion_guardia(
            paciente_id=999999,
            medico_id=medico.pk,
        )
