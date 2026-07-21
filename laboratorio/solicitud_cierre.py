"""
Cierre automático de SolicitudExamen al completar resultados y envío de informes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import MuestraAccionError, aplicar_iniciar_proceso
from laboratorio.resultado_muestra_validacion import (
    MUESTRA_ESTADOS_INVALIDOS_VALIDACION_ORDEN,
    asegurar_muestra_lista_para_carga,
)
from laboratorio.solicitud_estado import (
    SolicitudEstadoTransitionError,
    apply_solicitud_estado_transition,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class SolicitudCierreError(ValueError):
    """No se puede cerrar la solicitud (resultados incompletos o muestras inválidas)."""


def solicitud_resultados_completos(solicitud: SolicitudExamen) -> bool:
    qs = solicitud.resultados.all()
    if not qs.exists():
        return False
    return not qs.filter(valor_obtenido="").exists()


def _preparar_muestras_para_cierre(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
) -> None:
    """
    Recepciona tubos TOMADA y los deja EN_PROCESO antes de validar el cierre.
    Evita fallos al finalizar cuando la muestra ya estaba vinculada al resultado.
    """
    muestra_ids = list(
        solicitud.resultados.filter(muestra_id__isnull=False)
        .values_list("muestra_id", flat=True)
        .distinct()
    )
    if not muestra_ids:
        return
    for m in Muestra.objects.select_for_update().filter(pk__in=muestra_ids):
        asegurar_muestra_lista_para_carga(m, actor=actor, view=view)
        m.refresh_from_db()
        if m.estado in ("RECIBIDA", "CONSERVADA"):
            try:
                aplicar_iniciar_proceso(m.pk, actor=actor, view=view)
            except MuestraAccionError:
                pass


def _validar_muestras_para_cierre(solicitud: SolicitudExamen) -> None:
    muestra_ids = list(
        solicitud.resultados.filter(muestra_id__isnull=False)
        .values_list("muestra_id", flat=True)
        .distinct()
    )
    if not muestra_ids:
        return
    for m in Muestra.objects.filter(pk__in=muestra_ids):
        if m.estado in MUESTRA_ESTADOS_INVALIDOS_VALIDACION_ORDEN:
            raise SolicitudCierreError(
                "Hay un resultado vinculado a una muestra en estado incompatible."
            )


def solicitud_tiene_algun_resultado(solicitud: SolicitudExamen) -> bool:
    return solicitud.resultados.exclude(valor_obtenido="").exists()


def solicitud_resultados_parciales(solicitud: SolicitudExamen) -> bool:
    return solicitud_tiene_algun_resultado(solicitud) and not solicitud_resultados_completos(solicitud)


def informar_parcial_si_corresponde(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
) -> bool:
    """
    Marca la orden como INFORMADO_PARCIAL si hay al menos un resultado cargado
    y aún faltan valores. Devuelve True si el estado es (o queda) informado parcial.
    """
    if solicitud.estado == "FINALIZADO":
        return False
    if not solicitud_resultados_parciales(solicitud):
        return False
    if solicitud.estado == "INFORMADO_PARCIAL":
        return True
    apply_solicitud_estado_transition(
        solicitud,
        "INFORMADO_PARCIAL",
        actor=actor,
        accion="informar_parcial",
        view=view,
    )
    return True


def finalizar_solicitud_si_completa(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    accion: str = "finalizar_auto",
    confirmar_criticos: bool = False,
) -> bool:
    """
    Pasa EN_PROCESO / INFORMADO_PARCIAL → FINALIZADO si todos los resultados tienen valor.
    Devuelve True si se aplicó la transición.

    Requiere confirmación explícita si hay resultados patológicos o críticos.
    """
    if solicitud.estado not in ("EN_PROCESO", "INFORMADO_PARCIAL"):
        return False
    if not solicitud_resultados_completos(solicitud):
        return False
    _preparar_muestras_para_cierre(solicitud, actor=actor, view=view)
    _validar_muestras_para_cierre(solicitud)

    qs = solicitud.resultados.all()
    tiene_alertas = qs.filter(es_patologico=True).exists() or qs.filter(es_critico=True).exists()
    if tiene_alertas and not confirmar_criticos:
        raise SolicitudCierreError(
            "Hay resultados patológicos o críticos. Confirme la liberación "
            "enviando confirmar_criticos=true."
        )

    before_resultados = {r.id: safe_model_snapshot(r) for r in qs}

    apply_solicitud_estado_transition(
        solicitud,
        "FINALIZADO",
        actor=actor,
        accion=accion,
        view=view,
    )

    now = timezone.now()
    solicitud.resultados.update(
        validado_por=actor,
        fecha_validacion=now,
    )
    solicitud.refresh_from_db()

    for res in ResultadoExamen.objects.filter(solicitud_id=solicitud.pk):
        log_update(
            actor=actor,
            entity=res,
            before=before_resultados[res.id],
            module="laboratorio",
            metadata={
                "action": accion,
                "accion": accion,
                "view": view,
            },
        )
    return True


def finalizar_solicitud_manual(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    confirmar_criticos: bool = False,
) -> None:
    """Cierre explícito (validación / liberación clínica)."""
    if solicitud.estado == "FINALIZADO":
        raise SolicitudEstadoTransitionError("La solicitud ya está finalizada.")
    if solicitud.estado != "EN_PROCESO" and solicitud.estado != "INFORMADO_PARCIAL":
        raise SolicitudEstadoTransitionError(
            "Solo se pueden finalizar solicitudes en proceso o informadas parcialmente."
        )
    if not solicitud_resultados_completos(solicitud):
        raise SolicitudCierreError(
            "No se puede finalizar una solicitud con resultados vacíos."
        )
    if not finalizar_solicitud_si_completa(
        solicitud,
        actor=actor,
        view=view,
        accion="validar",
        confirmar_criticos=confirmar_criticos,
    ):
        raise SolicitudCierreError("No se pudo finalizar la solicitud.")
