"""Restricciones de frecuencia de ensayos (obra social / política clínica)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterable

from django.utils import timezone

from laboratorio.models import SolicitudExamen, TipoExamen
from usuarios.roles import es_operador_lims

CODIGO_PROBNP = "PROBNP"
VENTANA_DIAS_PROBNP = 31

MENSAJE_PROBNP_FRECUENCIA = (
    "La Obra Social no le permite realizar la determinación de proBNP debido a "
    "que tiene ya una realizada hace menos de 1 mes, de querer de todas maneras "
    "realizar el ensayo consulte con el Laboratorio"
)


class RestriccionFrecuenciaError(ValueError):
    """El usuario no puede agregar el ensayo por política de frecuencia."""


def paciente_tiene_probnp_reciente(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> bool:
    """True si el paciente ya tiene un pedido con PROBNP en la ventana."""
    desde = timezone.now() - timedelta(days=VENTANA_DIAS_PROBNP)
    qs = SolicitudExamen.objects.filter(
        paciente_id=paciente_id,
        fecha_solicitud__gte=desde,
        tipos_examen__codigo=CODIGO_PROBNP,
    )
    if exclude_solicitud_id is not None:
        qs = qs.exclude(pk=exclude_solicitud_id)
    return qs.exists()


def tipos_incluyen_probnp(tipo_examen_ids: Iterable[int]) -> bool:
    ids = list(tipo_examen_ids)
    if not ids:
        return False
    return TipoExamen.objects.filter(pk__in=ids, codigo=CODIGO_PROBNP).exists()


def assert_puede_agregar_probnp(
    user: Any,
    paciente_id: int,
    tipo_examen_ids: Iterable[int],
    *,
    exclude_solicitud_id: int | None = None,
) -> None:
    """
    Bloquea agregar PROBNP si hay pedido reciente, salvo operadores LIMS
    (laboratorio / bioquímico).
    """
    if es_operador_lims(user):
        return
    if not tipos_incluyen_probnp(tipo_examen_ids):
        return
    if paciente_tiene_probnp_reciente(
        paciente_id, exclude_solicitud_id=exclude_solicitud_id
    ):
        raise RestriccionFrecuenciaError(MENSAJE_PROBNP_FRECUENCIA)


def restricciones_ensayos_para(user: Any, paciente_id: int) -> dict[str, dict[str, Any]]:
    """Payload para UX: qué ensayos están bloqueados para este usuario/paciente."""
    if es_operador_lims(user):
        return {
            CODIGO_PROBNP: {"bloqueado": False, "mensaje": None},
        }
    if paciente_tiene_probnp_reciente(paciente_id):
        return {
            CODIGO_PROBNP: {
                "bloqueado": True,
                "mensaje": MENSAJE_PROBNP_FRECUENCIA,
            },
        }
    return {
        CODIGO_PROBNP: {"bloqueado": False, "mensaje": None},
    }
