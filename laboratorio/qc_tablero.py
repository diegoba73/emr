"""Tablero IQC de la mañana: estado por equipo y por ensayo."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from laboratorio.equipos_lab import (
    EXAMENES_POR_EQUIPO,
    codigo_equipo_canonico,
    es_equipo_por_ensayo,
)
from laboratorio.models import SolicitudExamen, TipoExamen
from laboratorio.models_qc import (
    Calibracion,
    CorridaQC,
    EquipoAnalizador,
    LoteControl,
    LoteProductoControl,
    MaterialControl,
    ProductoControl,
)
from laboratorio.qc_service import (
    _ultima_corrida_producto,
    _ventana_hoy,
    materiales_iqc_canonicos,
)
from laboratorio.solicitud_orden_abierta import ESTADOS_ORDEN_EN_CURSO

logger = logging.getLogger(__name__)


def _estado_nivel(corrida: CorridaQC | None) -> str:
    if corrida is None:
        return "falta"
    if corrida.estado == CorridaQC.Estado.ACEPTADA:
        return "aceptada"
    if corrida.estado == CorridaQC.Estado.RECHAZADA:
        return "rechazada"
    return "pendiente"


def _pack_nivel(corrida: CorridaQC | None) -> dict[str, Any]:
    est = _estado_nivel(corrida)
    return {
        "estado": est,
        "corrida_id": corrida.id if corrida else None,
    }


def _rollup(s1: str, s2: str) -> tuple[str, str]:
    if s1 == "rechazada" or s2 == "rechazada":
        cual = "S1" if s1 == "rechazada" else "S2"
        return "no_ok", f"Control {cual} no OK — calibrar y repetir"
    if s1 == "aceptada" and s2 == "aceptada":
        return "liberado", "Liberado"
    faltan = []
    if s1 != "aceptada":
        faltan.append("S1")
    if s2 != "aceptada":
        faltan.append("S2")
    return "falta", "Falta " + " y ".join(faltan)


def _exam_ids_abiertos() -> set[int]:
    """Ensayos de órdenes en curso (y pedidos recientes), sin recorrer cada solicitud."""
    desde = timezone.now() - timedelta(days=14)
    qs = SolicitudExamen.objects.filter(
        Q(estado__in=ESTADOS_ORDEN_EN_CURSO)
        | Q(estado="PENDIENTE", fecha_solicitud__gte=desde)
    )
    ids = set(qs.values_list("tipos_examen", flat=True))
    ids.update(qs.values_list("paneles__tipos_examen", flat=True))
    ids.discard(None)
    return {int(i) for i in ids}


def _ensayos_de_equipo(eq: EquipoAnalizador, exam_ids_hoy: set[int]) -> list[dict[str, Any]]:
    canon = codigo_equipo_canonico(eq.codigo)
    codigos = EXAMENES_POR_EQUIPO.get(canon, frozenset())
    qs = TipoExamen.objects.filter(id__in=exam_ids_hoy, activo=True)
    out: list[dict[str, Any]] = []
    for te in qs.order_by("codigo"):
        code = (te.codigo or "").strip().upper()
        del_eq = te.equipo_analizador_id == eq.id
        del_lista = code in codigos
        if not (del_eq or del_lista):
            continue
        out.append({"id": te.id, "codigo": te.codigo, "nombre": te.nombre})
    return out


def _lote_producto_vigente(producto: ProductoControl) -> LoteProductoControl | None:
    return (
        LoteProductoControl.objects.filter(producto=producto, activo=True)
        .order_by("-vencimiento", "-id")
        .first()
    )


def _lote_material_vigente(material: MaterialControl) -> LoteControl | None:
    return (
        LoteControl.objects.filter(material=material, activo=True)
        .order_by("-vencimiento", "-id")
        .first()
    )


def _ultima_corrida_material(material: MaterialControl, equipo: EquipoAnalizador, *, start, end):
    return (
        CorridaQC.objects.filter(
            lote_control__material=material,
            equipo_id=equipo.id,
            fecha__gte=start,
            fecha__lt=end,
        )
        .order_by("-fecha", "-id")
        .first()
    )


def _calibracion_hoy(equipo: EquipoAnalizador, *, fecha) -> Calibracion | None:
    return Calibracion.objects.filter(equipo=equipo, fecha=fecha).order_by("-id").first()


def tablero_iqc_hoy() -> dict[str, Any]:
    start, end = _ventana_hoy()
    hoy = timezone.localdate()
    try:
        exam_ids_hoy = _exam_ids_abiertos()
    except Exception:
        logger.exception("tablero_iqc_hoy: no se pudieron listar ensayos de órdenes abiertas")
        exam_ids_hoy = set()
    equipos = list(EquipoAnalizador.objects.filter(activo=True).order_by("codigo"))
    cards: list[dict[str, Any]] = []

    for eq in equipos:
        try:
            cards.append(_card_equipo(eq, exam_ids_hoy, start, end, hoy))
        except Exception:
            logger.exception("tablero_iqc_hoy: equipo %s", eq.codigo)
            cards.append(
                {
                    "id": eq.id,
                    "codigo": eq.codigo,
                    "nombre": eq.nombre,
                    "modo": "POR_ENSAYO" if es_equipo_por_ensayo(eq.codigo) else "MULTIPARAM",
                    "estado": "sin_trabajo",
                    "resumen": "No se pudo armar esta tarjeta",
                    "tiene_trabajo": False,
                    "calibracion_hoy": None,
                    "producto": None,
                    "lote_producto_id": None,
                    "lote_codigo": None,
                    "s1": None,
                    "s2": None,
                    "ensayos_hoy": [],
                    "ensayos": [],
                }
            )

    return {"fecha": str(hoy), "equipos": cards}


def _card_equipo(eq, exam_ids_hoy, start, end, hoy) -> dict[str, Any]:
    ensayos_hoy = _ensayos_de_equipo(eq, exam_ids_hoy)
    cal = _calibracion_hoy(eq, fecha=hoy)
    cal_pack = (
        {"id": cal.id, "fecha": str(cal.fecha), "observaciones": cal.observaciones or ""}
        if cal
        else None
    )

    if es_equipo_por_ensayo(eq.codigo):
        exam_ids = {e["id"] for e in ensayos_hoy}
        if not exam_ids:
            exam_ids = set(
                MaterialControl.objects.filter(activo=True, equipo_id=eq.id).values_list(
                    "tipo_examen_id", flat=True
                )
            )
        mats = materiales_iqc_canonicos(exam_ids)
        por_exam: dict[int, dict[str, MaterialControl]] = {}
        for mat in mats:
            if mat.equipo_id != eq.id:
                continue
            por_exam.setdefault(mat.tipo_examen_id, {})[mat.nivel] = mat
        filas = []
        for te in TipoExamen.objects.filter(id__in=por_exam.keys()).order_by("codigo"):
            n1 = por_exam[te.id].get(CorridaQC.Nivel.N1) or por_exam[te.id].get("N1")
            n2 = por_exam[te.id].get(CorridaQC.Nivel.N2) or por_exam[te.id].get("N2")
            c1 = _ultima_corrida_material(n1, eq, start=start, end=end) if n1 else None
            c2 = _ultima_corrida_material(n2, eq, start=start, end=end) if n2 else None
            p1 = _pack_nivel(c1)
            p2 = _pack_nivel(c2)
            if n1:
                lote1 = _lote_material_vigente(n1)
                p1.update(
                    {
                        "material_id": n1.id,
                        "lote_control_id": lote1.id if lote1 else None,
                        "lote_codigo": lote1.codigo_lote if lote1 else None,
                    }
                )
            if n2:
                lote2 = _lote_material_vigente(n2)
                p2.update(
                    {
                        "material_id": n2.id,
                        "lote_control_id": lote2.id if lote2 else None,
                        "lote_codigo": lote2.codigo_lote if lote2 else None,
                    }
                )
            est, resumen = _rollup(
                p1["estado"] if n1 else "aceptada",
                p2["estado"] if n2 else "aceptada",
            )
            if not n1 and not n2:
                est, resumen = "sin_trabajo", "Sin material de control"
            pedido = te.id in {e["id"] for e in ensayos_hoy}
            filas.append(
                {
                    "tipo_examen": te.id,
                    "codigo": te.codigo,
                    "nombre": te.nombre,
                    "estado": est,
                    "resumen": resumen,
                    "pedido_hoy": pedido,
                    "s1": p1,
                    "s2": p2,
                }
            )
        relevantes = [f for f in filas if f["pedido_hoy"]] or filas
        if not filas:
            estado_eq, resumen_eq = "sin_trabajo", "Sin ensayos configurados"
        elif any(f["estado"] == "no_ok" for f in relevantes):
            estado_eq, resumen_eq = "no_ok", "Hay un control no OK"
        elif all(f["estado"] == "liberado" for f in relevantes):
            estado_eq, resumen_eq = "liberado", "Ensayos de hoy liberados"
        else:
            estado_eq, resumen_eq = "falta", "Faltan controles por ensayo"
        return {
            "id": eq.id,
            "codigo": eq.codigo,
            "nombre": eq.nombre,
            "modo": "POR_ENSAYO",
            "estado": estado_eq,
            "resumen": resumen_eq,
            "tiene_trabajo": bool(ensayos_hoy) or bool(filas),
            "calibracion_hoy": cal_pack,
            "producto": None,
            "lote_producto_id": None,
            "lote_codigo": None,
            "s1": None,
            "s2": None,
            "ensayos_hoy": ensayos_hoy,
            "ensayos": filas,
        }

    producto = (
        ProductoControl.objects.filter(
            equipo_id=eq.id, activo=True, modo=ProductoControl.Modo.MULTIPARAM
        )
        .order_by("id")
        .first()
    )
    lote = _lote_producto_vigente(producto) if producto else None
    c1 = c2 = None
    if producto:
        c1 = _ultima_corrida_producto(producto, eq, CorridaQC.Nivel.N1, start=start, end=end)
        c2 = _ultima_corrida_producto(producto, eq, CorridaQC.Nivel.N2, start=start, end=end)
    p1 = _pack_nivel(c1)
    p2 = _pack_nivel(c2)
    if lote:
        p1["lote_producto_id"] = lote.id
        p2["lote_producto_id"] = lote.id
        p1["lote_codigo"] = lote.codigo_lote
        p2["lote_codigo"] = lote.codigo_lote
    if producto:
        estado_eq, resumen_eq = _rollup(p1["estado"], p2["estado"])
        tiene = True
    else:
        estado_eq, resumen_eq = "sin_trabajo", "Sin producto de control"
        tiene = False
    liberado = estado_eq == "liberado"
    ensayos_pack = [
        {**e, "liberado": liberado, "razon": None if liberado else resumen_eq}
        for e in ensayos_hoy
    ]
    return {
        "id": eq.id,
        "codigo": eq.codigo,
        "nombre": eq.nombre,
        "modo": "MULTIPARAM",
        "estado": estado_eq,
        "resumen": resumen_eq,
        "tiene_trabajo": tiene,
        "calibracion_hoy": cal_pack,
        "producto": (
            {"id": producto.id, "codigo": producto.codigo, "nombre": producto.nombre}
            if producto
            else None
        ),
        "lote_producto_id": lote.id if lote else None,
        "lote_codigo": lote.codigo_lote if lote else None,
        "s1": p1,
        "s2": p2,
        "ensayos_hoy": ensayos_pack,
        "ensayos": [],
    }
