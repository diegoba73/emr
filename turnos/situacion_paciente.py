"""
Exclusividad de situación clínica del paciente.

Un paciente no puede tener en paralelo situaciones incompatibles:
- Internación activa
- Atención de guardia abierta
- Atención ambulatoria abierta

La transición guardia/ambulatoria → internación se permite cuando
``atencion_origen`` apunta a la atencion abierta que se está derivando;
esa atencion se cierra al admitir.
"""
from __future__ import annotations

from django.utils import timezone


class SituacionPacienteConflictError(Exception):
    """El paciente ya tiene otra situación clínica activa incompatible."""


ESTADOS_ATENCION_ACTIVOS = ("ABIERTA", "EN_REVISION")
CONTEXTO_AMBULATORIA = "AMBULATORIA"
CONTEXTO_GUARDIA = "GUARDIA"
CONTEXTO_INTERNACION = "INTERNACION"
CONTEXTOS_EXCLUSIVOS = (CONTEXTO_AMBULATORIA, CONTEXTO_GUARDIA)


def paciente_tiene_internacion_activa(paciente_id: int) -> bool:
    from internacion.models import Internacion

    return Internacion.objects.filter(paciente_id=paciente_id, activo=True).exists()


def atenciones_ambulatoria_guardia_abiertas(
    paciente_id: int,
    *,
    exclude_atencion_id: int | None = None,
):
    from turnos.models import Atencion

    qs = Atencion.objects.filter(
        paciente_id=paciente_id,
        estado_clinico__in=ESTADOS_ATENCION_ACTIVOS,
        contexto_atencion__in=CONTEXTOS_EXCLUSIVOS,
    ).order_by("id")
    if exclude_atencion_id is not None:
        qs = qs.exclude(pk=exclude_atencion_id)
    return qs


def assert_puede_iniciar_atencion_ambulatoria_o_guardia(
    paciente_id: int,
    contexto: str,
    *,
    exclude_atencion_id: int | None = None,
) -> None:
    """
    Valida que el paciente pueda iniciar una atención AMBULATORIA o GUARDIA.

    Raises:
        SituacionPacienteConflictError: si hay internación activa u otra
            atención ambulatoria/guardia abierta incompatible.
    """
    if contexto not in CONTEXTOS_EXCLUSIVOS:
        raise ValueError(
            f"contexto inválido para exclusividad ambulatoria/guardia: {contexto}"
        )

    if paciente_tiene_internacion_activa(paciente_id):
        raise SituacionPacienteConflictError(
            "El paciente está internado; no puede iniciar una atención "
            "ambulatoria ni de guardia. Debe dar de alta la internación primero."
        )

    abierta = atenciones_ambulatoria_guardia_abiertas(
        paciente_id, exclude_atencion_id=exclude_atencion_id
    ).first()
    if abierta is None:
        return

    label_abierta = abierta.get_contexto_atencion_display().lower()
    label_nueva = (
        "ambulatoria" if contexto == CONTEXTO_AMBULATORIA else "de guardia"
    )
    if abierta.contexto_atencion == contexto:
        raise SituacionPacienteConflictError(
            f"El paciente ya tiene una atención {label_abierta} abierta "
            f"(#{abierta.pk}). Debe cerrarla antes de iniciar otra."
        )
    raise SituacionPacienteConflictError(
        f"El paciente tiene una atención {label_abierta} abierta "
        f"(#{abierta.pk}). No puede iniciar una atención {label_nueva} en paralelo."
    )


def assert_puede_admitir_internacion(
    paciente_id: int,
    *,
    atencion_origen_id: int | None = None,
) -> None:
    """
    Valida admisión a internación respecto de otras situaciones activas.

    Permite derivar desde una unica atención ambulatoria/guardia abierta
    cuando ``atencion_origen_id`` apunta a esa atencion.
    """
    from turnos.models import Atencion

    if paciente_tiene_internacion_activa(paciente_id):
        from internacion.models import Internacion

        actual = (
            Internacion.objects.filter(paciente_id=paciente_id, activo=True)
            .select_related("cama__sector")
            .first()
        )
        cama = actual.cama if actual else None
        if cama is not None:
            raise SituacionPacienteConflictError(
                f"El paciente ya está internado en la cama {cama.nombre} "
                f"(Sector: {cama.sector.nombre}). "
                "Debe dar de alta al paciente antes de ingresarlo a otra cama."
            )
        raise SituacionPacienteConflictError(
            "El paciente ya tiene una internación activa. "
            "Debe dar de alta antes de admitir nuevamente."
        )

    abiertas = list(atenciones_ambulatoria_guardia_abiertas(paciente_id))
    if not abiertas:
        if atencion_origen_id is None:
            return
        origen = Atencion.objects.filter(pk=atencion_origen_id).first()
        if origen is None:
            raise SituacionPacienteConflictError(
                f"La atención de origen #{atencion_origen_id} no existe."
            )
        if origen.paciente_id != paciente_id:
            raise SituacionPacienteConflictError(
                "La atención de origen no pertenece al paciente indicado."
            )
        return

    if atencion_origen_id is None:
        abierta = abiertas[0]
        label = abierta.get_contexto_atencion_display().lower()
        raise SituacionPacienteConflictError(
            f"El paciente tiene una atención {label} abierta (#{abierta.pk}). "
            "Debe cerrarla o derivarla a internación (atencion_origen) antes de admitir."
        )

    origen = Atencion.objects.filter(pk=atencion_origen_id).first()
    if origen is None:
        raise SituacionPacienteConflictError(
            f"La atención de origen #{atencion_origen_id} no existe."
        )
    if origen.paciente_id != paciente_id:
        raise SituacionPacienteConflictError(
            "La atención de origen no pertenece al paciente indicado."
        )
    if origen.contexto_atencion not in CONTEXTOS_EXCLUSIVOS:
        raise SituacionPacienteConflictError(
            "La atención de origen debe ser ambulatoria o de guardia."
        )

    for abierta in abiertas:
        if abierta.pk != atencion_origen_id:
            label = abierta.get_contexto_atencion_display().lower()
            raise SituacionPacienteConflictError(
                f"El paciente tiene otra atencion {label} abierta (#{abierta.pk}) "
                "además de la atención de origen. Debe cerrarla antes de admitir."
            )


def finalizar_ambulatorias_abiertas_previas(paciente_id: int) -> list[int]:
    """
    Cierra atenciones ambulatorias ABIERTAS de encuentros anteriores.

    En agenda, el médico suele cerrar el drawer sin «Guardar y cerrar».
    Esa atención queda ABIERTA y bloqueaba el próximo turno del mismo paciente.
    No toca guardia ni internación.
    """
    from turnos.models import Atencion

    ids: list[int] = []
    qs = Atencion.objects.filter(
        paciente_id=paciente_id,
        estado_clinico=Atencion.EstadoClinico.ABIERTA,
        contexto_atencion=CONTEXTO_AMBULATORIA,
    ).order_by("id")
    for atencion in qs:
        if finalizar_atencion_por_derivacion(atencion):
            ids.append(atencion.pk)
    return ids


def finalizar_atencion_por_derivacion(atencion) -> bool:
    """
    Cierra una atención ambulatoria/guardia al derivarla a internación.

    Returns:
        True si se cerró ahora; False si ya estaba finalizada.
    """
    from turnos.models import Atencion

    if atencion.estado_clinico == Atencion.EstadoClinico.FINALIZADA:
        return False
    atencion.estado_clinico = Atencion.EstadoClinico.FINALIZADA
    atencion.fecha_cierre = timezone.now()
    atencion.save(update_fields=["estado_clinico", "fecha_cierre", "updated_at"])
    return True