"""Reglas de acceso clínico a archivos por paciente (C6.2)."""

from __future__ import annotations

from historias_clinicas.models import Consulta
from turnos.models import Atencion, Turno


def paciente_ids_vinculados_a_medico(medico) -> set[int]:
    """Pacientes vinculados por consulta HC, atención moderna o turno."""
    ids: set[int] = set()
    ids.update(
        Consulta.objects.filter(medico=medico)
        .values_list('historia_clinica__paciente_id', flat=True)
    )
    ids.update(
        Atencion.objects.filter(medico_principal=medico).values_list('paciente_id', flat=True)
    )
    ids.update(
        Turno.objects.filter(medico=medico).values_list('paciente_id', flat=True)
    )
    return {i for i in ids if i}


def medico_puede_acceder_paciente(medico, paciente) -> bool:
    return paciente.id in paciente_ids_vinculados_a_medico(medico)
