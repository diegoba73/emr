"""Visibilidad y propiedad de turnos por rol (alineado con ``TurnoViewSet.get_queryset``)."""

from __future__ import annotations

from archivos_medicos.access import paciente_ids_vinculados_a_medico

_TIPOS_RECURSO_ESTUDIO_TURNOS = frozenset({'SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'})


def medico_es_dueno_turno(medico, turno) -> bool:
    """
    True si el médico puede operar el turno (consulta propia o estudio vinculado).

    Coincide con el filtro de agenda del médico en ``TurnoViewSet.get_queryset``.
    """
    if turno.medico_id == medico.id:
        return True

    ec = getattr(turno, 'estudio_complementario', None)
    if ec is not None and getattr(ec, 'medico_solicitante_id', None) == medico.id:
        return True

    if turno.medico_id is None:
        recurso = getattr(turno, 'recurso', None)
        tipo = getattr(recurso, 'tipo_recurso', None) if recurso else None
        if tipo in _TIPOS_RECURSO_ESTUDIO_TURNOS:
            return turno.paciente_id in paciente_ids_vinculados_a_medico(medico)

    return False
