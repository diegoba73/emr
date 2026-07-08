"""
Transiciones de estado controladas para SolicitudExamen (LIMS nativo).
Estados: PENDIENTE → EN_PROCESO (toma de muestra) → INFORMADO_PARCIAL (informe parcial) → FINALIZADO.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from .models import SolicitudExamen


class SolicitudEstadoTransitionError(ValueError):
    """Transición de estado no permitida para la acción solicitada."""


# (accion, estado_origen, estado_destino)
_ALLOWED_TRANSITIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("tomar_muestra", "PENDIENTE", "EN_PROCESO"),
        ("informar_parcial", "EN_PROCESO", "INFORMADO_PARCIAL"),
        ("finalizar", "EN_PROCESO", "FINALIZADO"),
        ("finalizar", "INFORMADO_PARCIAL", "FINALIZADO"),
        ("finalizar_auto", "EN_PROCESO", "FINALIZADO"),
        ("finalizar_auto", "INFORMADO_PARCIAL", "FINALIZADO"),
        # Alias legacy API
        ("validar", "EN_PROCESO", "FINALIZADO"),
        ("validar", "INFORMADO_PARCIAL", "FINALIZADO"),
    }
)

ESTADOS_SOLICITUD_TERMINALES = frozenset({"FINALIZADO"})


def transicion_permitida(accion: str, estado_origen: str, estado_destino: str) -> bool:
    return (accion, estado_origen, estado_destino) in _ALLOWED_TRANSITIONS


def apply_solicitud_estado_transition(
    solicitud: SolicitudExamen,
    nuevo_estado: str,
    *,
    actor: AbstractUser | None,
    accion: str,
    view: str,
    extra_metadata: dict | None = None,
) -> SolicitudExamen:
    """
    Aplica un cambio de estado validado y registra auditoría.

    La instancia debe estar acotada a una transacción atómica; el llamador debe
    haber obtenido la fila con select_for_update() si hay riesgo de concurrencia.
    """
    estado_anterior = solicitud.estado

    if not transicion_permitida(accion, estado_anterior, nuevo_estado):
        raise SolicitudEstadoTransitionError(
            "Transición de estado no permitida para esta acción y estado actual."
        )

    before = safe_model_snapshot(solicitud)
    solicitud.estado = nuevo_estado
    solicitud.save(update_fields=["estado"])
    solicitud.refresh_from_db()

    metadata = {
        "accion": accion,
        "estado_anterior": estado_anterior,
        "estado_nuevo": nuevo_estado,
        "solicitud_id": solicitud.pk,
        "numero_solicitud": solicitud.numero,
        "view": view,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    log_update(
        actor=actor,
        entity=solicitud,
        before=before,
        module="laboratorio",
        metadata=metadata,
    )
    return solicitud
