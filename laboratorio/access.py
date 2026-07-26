"""Reglas de visibilidad clínica LIMS (lectura por vínculo de paciente)."""
from __future__ import annotations

from django.db.models import Q, QuerySet


def q_lectura_lims_medico(user, *, solicitud_path: str = "") -> Q:
    """
    Órdenes visibles para un médico en lectura:

    - propias (``medico_interno.user`` = usuario), o
    - de pacientes con vínculo clínico (turno, consulta HC o atención).

    ``solicitud_path`` vacío filtra sobre ``SolicitudExamen``; para relaciones
    anidadas usar p. ej. ``\"solicitud\"`` o ``\"estudio__solicitud\"``.
    """
    def field(name: str) -> str:
        return f"{solicitud_path}__{name}" if solicitud_path else name

    own = Q(**{field("medico_interno__user"): user})
    try:
        medico = user.medico
    except Exception:
        return own

    from archivos_medicos.access import paciente_ids_vinculados_a_medico

    ids = paciente_ids_vinculados_a_medico(medico)
    if not ids:
        return own
    return own | Q(**{f"{field('paciente_id')}__in": ids})


def filtrar_lectura_lims_medico(queryset: QuerySet, user, *, solicitud_path: str = "") -> QuerySet:
    """Aplica ``q_lectura_lims_medico`` al queryset."""
    return queryset.filter(q_lectura_lims_medico(user, solicitud_path=solicitud_path)).distinct()
