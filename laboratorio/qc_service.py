"""Servicios QC: evaluación de puntos, gate de liberación, serie LJ."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from laboratorio.models_qc import CorridaQC, MaterialControl, PuntoQC
from laboratorio.qc_westgard import evaluate_punto

logger = logging.getLogger(__name__)


class QcGateError(ValueError):
    """QC no vigente para liberación clínica."""


def _prev_puntos_material(material_id: int, exclude_punto_id: int | None = None, limit: int = 20):
    qs = (
        PuntoQC.objects.filter(corrida__lote_control__material_id=material_id)
        .order_by("-created_at")
        .select_related("corrida")[: limit + 5]
    )
    out = []
    for p in reversed(list(qs)):
        if exclude_punto_id and p.id == exclude_punto_id:
            continue
        out.append({"valor": float(p.valor), "z": p.z_score})
    return out[-limit:]


@transaction.atomic
def evaluar_y_guardar_punto(corrida: CorridaQC, valor: Decimal | float) -> PuntoQC:
    material = corrida.lote_control.material
    mean = float(material.media_target)
    sd = float(material.de_target)
    prev = _prev_puntos_material(material.id)
    result = evaluate_punto(float(valor), mean, sd, prev)
    punto = PuntoQC.objects.create(
        corrida=corrida,
        valor=Decimal(str(valor)),
        z_score=result["z"],
        reglas_disparadas=result["rules"],
        fuera_control=result["fuera_control"],
        warning=result["warning"],
    )
    if result["fuera_control"]:
        corrida.estado = CorridaQC.Estado.RECHAZADA
        corrida.save(update_fields=["estado", "updated_at"])
    return punto


def finalizar_corrida(corrida: CorridaQC) -> CorridaQC:
    if corrida.puntos.filter(fuera_control=True).exists():
        corrida.estado = CorridaQC.Estado.RECHAZADA
    elif corrida.puntos.exists():
        corrida.estado = CorridaQC.Estado.ACEPTADA
    else:
        corrida.estado = CorridaQC.Estado.PENDIENTE
    corrida.save(update_fields=["estado", "updated_at"])
    return corrida


def levey_jennings_series(material: MaterialControl, limit: int = 60) -> dict[str, Any]:
    puntos = (
        PuntoQC.objects.filter(corrida__lote_control__material=material)
        .select_related("corrida")
        .order_by("corrida__fecha", "id")[:limit]
    )
    return {
        "material_id": material.id,
        "material_nombre": material.nombre,
        "tipo_examen_codigo": material.tipo_examen.codigo,
        "media_target": float(material.media_target),
        "de_target": float(material.de_target),
        "puntos": [
            {
                "id": p.id,
                "fecha": p.corrida.fecha.isoformat(),
                "valor": float(p.valor),
                "z_score": p.z_score,
                "fuera_control": p.fuera_control,
                "warning": p.warning,
                "reglas": p.reglas_disparadas or [],
            }
            for p in puntos
        ],
    }


def validar_qc_para_cierre(
    solicitud,
    *,
    confirmar_qc_override: bool = False,
    motivo_override: str = "",
    actor=None,
) -> None:
    """Bloquea validación clínica si hay QC configurado y corrida inválida hoy.

    Por cada material activo del examen: se mira la **última** corrida del día.
    Un rechazo previo no bloquea si luego hubo una corrida aceptada (re-run).
    """
    exam_ids = set(solicitud.tipos_examen.values_list("id", flat=True))
    for panel in solicitud.paneles.prefetch_related("tipos_examen").all():
        exam_ids.update(panel.tipos_examen.values_list("id", flat=True))
    if not exam_ids:
        exam_ids = set(
            solicitud.resultados.values_list("tipo_examen_id", flat=True).distinct()
        )
    materiales = MaterialControl.objects.filter(activo=True, tipo_examen_id__in=exam_ids)
    if not materiales.exists():
        return

    hoy = timezone.localdate()
    start = timezone.make_aware(datetime.combine(hoy, time.min))
    end = start + timedelta(days=1)

    nivel_label = {"N1": "S1", "N2": "S2", "N3": "N3"}
    problemas: list[str] = []
    for mat in materiales.select_related("tipo_examen"):
        ultima = (
            CorridaQC.objects.filter(
                lote_control__material=mat,
                fecha__gte=start,
                fecha__lt=end,
            )
            .order_by("-fecha", "-id")
            .first()
        )
        tag = f"{mat.tipo_examen.codigo} {nivel_label.get(mat.nivel, mat.nivel)}"
        if ultima is None:
            problemas.append(f"Sin corrida QC hoy para {tag}")
        elif ultima.estado == CorridaQC.Estado.RECHAZADA:
            problemas.append(f"QC rechazado hoy para {tag} (última corrida)")
        elif ultima.estado != CorridaQC.Estado.ACEPTADA:
            problemas.append(f"QC pendiente hoy para {tag}")

    if not problemas:
        return

    role = (getattr(actor, "rol", "") or "").lower() if actor else ""
    is_admin = bool(actor and (getattr(actor, "is_superuser", False) or role == "admin"))
    if confirmar_qc_override and is_admin and motivo_override.strip():
        logger.warning(
            "QC override admin solicitud=%s actor=%s motivo=%s problemas=%s",
            getattr(solicitud, "id", None),
            getattr(actor, "id", None),
            motivo_override,
            problemas,
        )
        try:
            from auditoria.audit_service import log_update

            log_update(
                actor=actor,
                entity=solicitud,
                before=None,
                module="laboratorio",
                metadata={
                    "accion": "qc_override",
                    "motivo": motivo_override,
                    "problemas": problemas,
                },
            )
        except Exception:
            pass
        return

    raise QcGateError(
        "Control de calidad no vigente: "
        + "; ".join(problemas)
        + ". Admin puede forzar con confirmar_qc_override y motivo_qc_override."
    )
