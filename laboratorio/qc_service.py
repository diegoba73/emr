"""Servicios QC: evaluación de puntos, gate de liberación, serie LJ."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from laboratorio.equipos_lab import EXAMENES_POR_EQUIPO, es_equipo_multiparam
from laboratorio.models import TipoExamen
from laboratorio.models_qc import (
    CorridaQC,
    EquipoAnalizador,
    MaterialControl,
    ProductoControl,
    PuntoQC,
    TargetLoteControl,
)
from laboratorio.qc_westgard import evaluate_punto

logger = logging.getLogger(__name__)

NIVEL_LABEL = {"N1": "S1", "N2": "S2", "N3": "N3"}
NIVELES_IQC_MULTIPARAM = (CorridaQC.Nivel.N1, CorridaQC.Nivel.N2)


class QcGateError(ValueError):
    """QC no vigente para liberación clínica o carga de resultados."""


def get_equipo_iqc_default() -> EquipoAnalizador | None:
    """Equipo IQC por defecto (CM260 u otro código configurado); si no, el primer activo."""
    codigo = (getattr(settings, "IQC_EQUIPO_DEFAULT_CODIGO", None) or "CM260").strip()
    if codigo:
        eq = EquipoAnalizador.objects.filter(codigo=codigo, activo=True).first()
        if eq:
            return eq
    return EquipoAnalizador.objects.filter(activo=True).order_by("codigo").first()


def equipo_para_material(mat: MaterialControl) -> EquipoAnalizador | None:
    """Equipo del material → equipo del TipoExamen → default CM260."""
    if getattr(mat, "equipo_id", None):
        return mat.equipo
    te = getattr(mat, "tipo_examen", None)
    if te is not None and getattr(te, "equipo_analizador_id", None):
        return te.equipo_analizador
    return get_equipo_iqc_default()


def _exam_ids_solicitud(solicitud) -> set[int]:
    exam_ids = set(solicitud.tipos_examen.values_list("id", flat=True))
    for panel in solicitud.paneles.prefetch_related("tipos_examen").all():
        exam_ids.update(panel.tipos_examen.values_list("id", flat=True))
    if not exam_ids:
        exam_ids = set(
            solicitud.resultados.values_list("tipo_examen_id", flat=True).distinct()
        )
    return exam_ids


def _ventana_hoy():
    hoy = timezone.localdate()
    start = timezone.make_aware(datetime.combine(hoy, time.min))
    end = start + timedelta(days=1)
    return start, end


def _producto_multiparam_para_examen(examen: TipoExamen) -> ProductoControl | None:
    """Producto MULTIPARAM activo que cubre este ensayo, o None (cae a material por ensayo)."""
    eq = getattr(examen, "equipo_analizador", None)
    if eq is None or not eq.activo:
        return None
    codigo_eq = (eq.codigo or "").strip().upper()
    if not es_equipo_multiparam(codigo_eq):
        return None

    producto = (
        ProductoControl.objects.filter(
            equipo_id=eq.id, activo=True, modo=ProductoControl.Modo.MULTIPARAM
        )
        .order_by("id")
        .first()
    )
    if producto is None:
        return None

    cubierto_por_lista = (examen.codigo or "").strip().upper() in EXAMENES_POR_EQUIPO.get(
        codigo_eq, frozenset()
    )
    cubierto_por_target = TargetLoteControl.objects.filter(
        lote__producto=producto,
        lote__activo=True,
        tipo_examen_id=examen.id,
    ).exists()
    if cubierto_por_lista or cubierto_por_target:
        return producto
    return None


def _ultima_corrida_producto(
    producto: ProductoControl,
    equipo: EquipoAnalizador,
    nivel: str,
    *,
    start,
    end,
) -> CorridaQC | None:
    return (
        CorridaQC.objects.filter(
            lote_producto__producto=producto,
            equipo_id=equipo.id,
            nivel=nivel,
            fecha__gte=start,
            fecha__lt=end,
        )
        .order_by("-fecha", "-id")
        .first()
    )


def _problemas_iqc_producto(
    producto: ProductoControl,
    equipo: EquipoAnalizador,
    *,
    start,
    end,
) -> list[str]:
    """Exige S1+S2 ACEPTADAS hoy del producto en ese equipo (última corrida por nivel)."""
    problemas: list[str] = []
    nombre = (producto.nombre or producto.codigo or "control").split()[0]
    for nivel in NIVELES_IQC_MULTIPARAM:
        tag = f"{nombre} {NIVEL_LABEL.get(nivel, nivel)}"
        ultima = _ultima_corrida_producto(producto, equipo, nivel, start=start, end=end)
        if ultima is None:
            sin_equipo = CorridaQC.objects.filter(
                lote_producto__producto=producto,
                nivel=nivel,
                equipo__isnull=True,
                fecha__gte=start,
                fecha__lt=end,
            ).exists()
            if sin_equipo:
                problemas.append(
                    f"Corrida QC hoy para {tag} sin equipo (no cuenta; use {equipo.codigo})"
                )
            else:
                problemas.append(f"Sin {tag} hoy en {equipo.codigo}")
        elif ultima.estado == CorridaQC.Estado.RECHAZADA:
            problemas.append(f"QC rechazado hoy para {tag} en {equipo.codigo} (última corrida)")
        elif ultima.estado != CorridaQC.Estado.ACEPTADA:
            problemas.append(f"QC pendiente hoy para {tag} en {equipo.codigo}")
    return problemas


def _problemas_iqc_materiales(materiales, *, equipo_forzado: EquipoAnalizador | None = None) -> list[str]:
    """Por cada material: última corrida de hoy en EL equipo de ese material."""
    if not materiales:
        return []

    start, end = _ventana_hoy()
    problemas: list[str] = []
    for mat in materiales:
        eq = equipo_forzado or equipo_para_material(mat)
        tag = f"{mat.tipo_examen.codigo} {NIVEL_LABEL.get(mat.nivel, mat.nivel)}"
        if eq is None:
            problemas.append(
                f"Sin equipo configurado para IQC de {tag} "
                f"(definir equipo del material/examen o {getattr(settings, 'IQC_EQUIPO_DEFAULT_CODIGO', 'CM260')})"
            )
            continue
        ultima = (
            CorridaQC.objects.filter(
                lote_control__material=mat,
                equipo_id=eq.id,
                fecha__gte=start,
                fecha__lt=end,
            )
            .order_by("-fecha", "-id")
            .first()
        )
        if ultima is None:
            sin_equipo = CorridaQC.objects.filter(
                lote_control__material=mat,
                equipo__isnull=True,
                fecha__gte=start,
                fecha__lt=end,
            ).exists()
            if sin_equipo:
                problemas.append(
                    f"Corrida QC hoy para {tag} sin equipo (no cuenta; use {eq.codigo})"
                )
            else:
                problemas.append(f"Sin corrida QC hoy para {tag} en {eq.codigo}")
        elif ultima.estado == CorridaQC.Estado.RECHAZADA:
            problemas.append(
                f"QC rechazado hoy para {tag} en {eq.codigo} (última corrida)"
            )
        elif ultima.estado != CorridaQC.Estado.ACEPTADA:
            problemas.append(f"QC pendiente hoy para {tag} en {eq.codigo}")
    return problemas


def estado_iqc_solicitud(solicitud, *, equipo: EquipoAnalizador | None = None) -> dict[str, Any]:
    """Precheck sin raise: {ok, aplicable, equipo, equipos, problemas}.

    Hybrid: ensayos cubiertos por ProductoControl MULTIPARAM exigen S1+S2 del producto
    (no una corrida por ensayo). El resto usa MaterialControl (VIDAS/Finecare / legado).
    ``equipo`` (opcional) fuerza un único equipo (tests legacy).
    """
    exam_ids = _exam_ids_solicitud(solicitud)
    examenes = list(
        TipoExamen.objects.filter(id__in=exam_ids).select_related("equipo_analizador")
    )
    start, end = _ventana_hoy()
    default_eq = get_equipo_iqc_default()

    productos_por_key: dict[tuple[int, int], tuple[ProductoControl, EquipoAnalizador]] = {}
    exam_ids_multiparam: set[int] = set()
    for ex in examenes:
        prod = _producto_multiparam_para_examen(ex)
        if prod is None:
            continue
        eq = ex.equipo_analizador
        if eq is None:
            continue
        exam_ids_multiparam.add(ex.id)
        productos_por_key[(prod.id, eq.id)] = (prod, eq)

    exam_ids_material = set(exam_ids) - exam_ids_multiparam
    materiales = list(
        MaterialControl.objects.filter(
            activo=True, tipo_examen_id__in=exam_ids_material
        ).select_related("tipo_examen", "tipo_examen__equipo_analizador", "equipo")
    )

    if not productos_por_key and not materiales:
        return {
            "ok": True,
            "aplicable": False,
            "equipo": (
                {"id": default_eq.id, "codigo": default_eq.codigo, "nombre": default_eq.nombre}
                if default_eq
                else None
            ),
            "equipos": [],
            "problemas": [],
        }

    problemas: list[str] = []
    equipos_map: dict[int, dict[str, Any]] = {}

    for prod, eq_prod in productos_por_key.values():
        eq_check = equipo or eq_prod
        problemas.extend(_problemas_iqc_producto(prod, eq_check, start=start, end=end))
        if eq_check.id not in equipos_map:
            equipos_map[eq_check.id] = {
                "id": eq_check.id,
                "codigo": eq_check.codigo,
                "nombre": eq_check.nombre,
            }

    problemas.extend(_problemas_iqc_materiales(materiales, equipo_forzado=equipo))
    for mat in materiales:
        eq_mat = equipo or equipo_para_material(mat)
        if eq_mat and eq_mat.id not in equipos_map:
            equipos_map[eq_mat.id] = {
                "id": eq_mat.id,
                "codigo": eq_mat.codigo,
                "nombre": eq_mat.nombre,
            }

    equipos = list(equipos_map.values())
    return {
        "ok": not problemas,
        "aplicable": True,
        "equipo": equipos[0]
        if len(equipos) == 1
        else (
            {"id": default_eq.id, "codigo": default_eq.codigo, "nombre": default_eq.nombre}
            if default_eq
            else None
        ),
        "equipos": equipos,
        "problemas": problemas,
    }


def verificar_iqc_para_solicitud(
    solicitud,
    *,
    equipo: EquipoAnalizador | None = None,
    confirmar_qc_override: bool = False,
    motivo_override: str = "",
    actor=None,
    permitir_override: bool = True,
) -> None:
    """Bloquea si falta QC ACEPTADO hoy (producto S1+S2 o material por ensayo).

    Corridas sin equipo no cuentan. Override solo admin/superuser cuando permitir_override.
    """
    estado = estado_iqc_solicitud(solicitud, equipo=equipo)
    if estado["ok"]:
        return

    problemas: list[str] = estado["problemas"]
    if permitir_override:
        role = (getattr(actor, "rol", "") or "").lower() if actor else ""
        is_admin = bool(
            actor and (getattr(actor, "is_superuser", False) or role == "admin")
        )
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
                        "equipo": estado.get("equipo"),
                    },
                )
            except Exception:
                pass
            return

    suffix = (
        ". Admin puede forzar con confirmar_qc_override y motivo_qc_override."
        if permitir_override
        else ". Ejecutá IQC en Control de calidad antes de cargar resultados."
    )
    raise QcGateError("Control de calidad no vigente: " + "; ".join(problemas) + suffix)


def validar_qc_para_cierre(
    solicitud,
    *,
    confirmar_qc_override: bool = False,
    motivo_override: str = "",
    actor=None,
) -> None:
    """Gate de liberación clínica (con override admin)."""
    verificar_iqc_para_solicitud(
        solicitud,
        confirmar_qc_override=confirmar_qc_override,
        motivo_override=motivo_override,
        actor=actor,
        permitir_override=True,
    )


def _prev_puntos_material(material_id: int, exclude_punto_id: int | None = None, limit: int = 20):
    """Historial para reglas multi-punto Westgard (material por ensayo).

    Omite puntos fuera de control y corridas RECHAZADAS: tras un rechazo el
    re-run no debe disparar R-4s / 2-2s contra el punto ya descartado.
    """
    qs = (
        PuntoQC.objects.filter(
            corrida__lote_control__material_id=material_id,
            fuera_control=False,
        )
        .exclude(corrida__estado=CorridaQC.Estado.RECHAZADA)
        .order_by("-created_at")
        .select_related("corrida")[: limit + 5]
    )
    out = []
    for p in reversed(list(qs)):
        if exclude_punto_id and p.id == exclude_punto_id:
            continue
        out.append({"valor": float(p.valor), "z": p.z_score})
    return out[-limit:]


def _prev_puntos_target(
    lote_producto_id: int,
    nivel: str,
    tipo_examen_id: int,
    exclude_punto_id: int | None = None,
    limit: int = 20,
):
    """Historial Westgard para un ensayo dentro de un lote+nivel de producto."""
    qs = (
        PuntoQC.objects.filter(
            corrida__lote_producto_id=lote_producto_id,
            corrida__nivel=nivel,
            tipo_examen_id=tipo_examen_id,
            fuera_control=False,
        )
        .exclude(corrida__estado=CorridaQC.Estado.RECHAZADA)
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
    if not corrida.lote_control_id:
        raise ValueError("evaluar_y_guardar_punto requiere lote_control (corrida por ensayo).")
    material = corrida.lote_control.material
    mean = float(material.media_target)
    sd = float(material.de_target)
    prev = _prev_puntos_material(material.id)
    result = evaluate_punto(float(valor), mean, sd, prev)
    punto = PuntoQC.objects.create(
        corrida=corrida,
        tipo_examen=material.tipo_examen,
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


@transaction.atomic
def evaluar_y_guardar_punto_multiparam(
    corrida: CorridaQC,
    tipo_examen: TipoExamen,
    valor: Decimal | float,
) -> PuntoQC:
    if not corrida.lote_producto_id or not corrida.nivel:
        raise ValueError("Corrida multiparámetro requiere lote_producto y nivel.")
    target = TargetLoteControl.objects.filter(
        lote_id=corrida.lote_producto_id,
        tipo_examen=tipo_examen,
        nivel=corrida.nivel,
    ).first()
    if target is None:
        raise ValueError(
            f"Sin target para {tipo_examen.codigo} {NIVEL_LABEL.get(corrida.nivel, corrida.nivel)} "
            f"en lote {corrida.lote_producto_id}."
        )
    mean = float(target.media_target)
    sd = float(target.de_target)
    prev = _prev_puntos_target(corrida.lote_producto_id, corrida.nivel, tipo_examen.id)
    result = evaluate_punto(float(valor), mean, sd, prev)
    punto = PuntoQC.objects.create(
        corrida=corrida,
        tipo_examen=tipo_examen,
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


def aceptar_nivel_rapido(corrida: CorridaQC) -> CorridaQC:
    """Aceptación rápida de nivel (sin valores por ensayo)."""
    obs = (corrida.observaciones or "").strip()
    if not obs:
        corrida.observaciones = "aceptación rápida de nivel"
    corrida.estado = CorridaQC.Estado.ACEPTADA
    corrida.save(update_fields=["estado", "observaciones", "updated_at"])
    return corrida


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
        "tipo_examen_id": material.tipo_examen_id,
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


def levey_jennings_por_examen(tipo_examen: TipoExamen, limit: int = 60) -> dict[str, Any]:
    """Serie LJ por ensayo: puntos de corridas por material + multiparámetro."""
    puntos = (
        PuntoQC.objects.filter(
            Q(tipo_examen=tipo_examen) | Q(corrida__lote_control__material__tipo_examen=tipo_examen)
        )
        .select_related("corrida", "tipo_examen")
        .order_by("corrida__fecha", "id")[:limit]
    )
    media = None
    de = None
    target = (
        TargetLoteControl.objects.filter(
            tipo_examen=tipo_examen, lote__activo=True, lote__producto__activo=True
        )
        .order_by("-lote__id", "nivel")
        .first()
    )
    if target:
        media = float(target.media_target)
        de = float(target.de_target)
    else:
        mat = MaterialControl.objects.filter(tipo_examen=tipo_examen, activo=True).order_by("nivel").first()
        if mat:
            media = float(mat.media_target)
            de = float(mat.de_target)
    return {
        "material_id": None,
        "material_nombre": tipo_examen.nombre,
        "tipo_examen_id": tipo_examen.id,
        "tipo_examen_codigo": tipo_examen.codigo,
        "media_target": media if media is not None else 0.0,
        "de_target": de if de is not None else 1.0,
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
