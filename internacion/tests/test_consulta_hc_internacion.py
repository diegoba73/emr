"""Tests de consulta HC vinculada a evoluciones de internación."""
import pytest

from historias_clinicas.models import Consulta
from historias_clinicas.services import consulta_hc_id_para_atencion, ensure_consulta_hc_desde_atencion
from internacion.models import Sector, Cama, Internacion
from internacion.services import InternacionClinicalService
from internacion.tests.helpers import unique_suffix
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente


@pytest.fixture
def medico(db):
    esp, _ = Especialidad.objects.get_or_create(nombre=f'Cardio-hc-{unique_suffix()}')
    return Medico.objects.create(
        matricula=f'M-HC-{unique_suffix()}',
        nombre='Ana',
        apellido='Ruiz',
        especialidad=esp,
    )


@pytest.fixture
def paciente(db):
    suffix = unique_suffix()
    return Paciente.objects.create(
        dni=f'HC-{suffix}',
        nombre='Luis',
        apellido='Díaz',
    )


@pytest.fixture
def internacion(db, paciente, medico):
    sector = Sector.objects.create(nombre=f'UCO-hc-{unique_suffix()}')
    cama = Cama.objects.create(
        nombre=f'C-hc-{unique_suffix()}',
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
def test_iniciar_evolucion_crea_consulta_hc(internacion, medico):
    outcome = InternacionClinicalService.iniciar_evolucion_internacion(
        internacion,
        medico=medico,
    )
    cid = consulta_hc_id_para_atencion(outcome.atencion)
    assert cid is not None
    consulta = Consulta.objects.get(pk=cid)
    assert consulta.atencion_id == outcome.atencion.pk
    assert consulta.historia_clinica_id == internacion.paciente_id


@pytest.mark.django_db
def test_ensure_consulta_hc_idempotente(internacion, medico):
    outcome = InternacionClinicalService.iniciar_evolucion_internacion(
        internacion,
        medico=medico,
    )
    first = ensure_consulta_hc_desde_atencion(outcome.atencion)
    second = ensure_consulta_hc_desde_atencion(outcome.atencion)
    assert first.pk == second.pk
    assert Consulta.objects.filter(atencion_id=outcome.atencion.pk).count() == 1
