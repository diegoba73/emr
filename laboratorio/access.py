"""Reglas de visibilidad clínica LIMS (lectura por vínculo de paciente)."""
from __future__ import annotations

from django.db.models import Q, QuerySet

# Órdenes ya informadas visibles en ficha aunque el médico no sea el solicitante
# (p. ej. historial LabWin / EXTERNO_ICPL sin medico_interno).
ESTADOS_LECTURA_HISTORIAL_MEDICO = ("FINALIZADO", "INFORMADO_PARCIAL")


def q_lectura_lims_medico(
    user,
    *,
    solicitud_path: str = "",
    paciente_id: int | None = None,
) -> Q:
    """
    Órdenes visibles para un médico en lectura:

    - propias (``medico_interno.user`` = usuario), o
    - de pacientes con vínculo clínico (turno, consulta HC o atención), o
    - si se consulta un ``paciente_id`` concreto: también las informadas
      (FINALIZADO / INFORMADO_PARCIAL) de ese paciente (historial en ficha).

    Sin ``paciente_id``, el listado global no incluye el historial de todos
    los pacientes del sistema.
    """
    def field(name: str) -> str:
        return f"{solicitud_path}__{name}" if solicitud_path else name

    own = Q(**{field("medico_interno__user"): user})
    q = own
    try:
        medico = user.medico
    except Exception:
        medico = None

    if medico is not None:
        from archivos_medicos.access import paciente_ids_vinculados_a_medico

        ids = paciente_ids_vinculados_a_medico(medico)
        if ids:
            q = q | Q(**{f"{field('paciente_id')}__in": ids})

    if paciente_id is not None:
        q = q | (
            Q(**{field("paciente_id"): paciente_id})
            & Q(**{f"{field('estado')}__in": ESTADOS_LECTURA_HISTORIAL_MEDICO})
        )

    return q


def filtrar_lectura_lims_medico(
    queryset: QuerySet,
    user,
    *,
    solicitud_path: str = "",
    paciente_id: int | None = None,
) -> QuerySet:
    """Aplica ``q_lectura_lims_medico`` al queryset."""
    return queryset.filter(
        q_lectura_lims_medico(
            user,
            solicitud_path=solicitud_path,
            paciente_id=paciente_id,
        )
    ).distinct()
