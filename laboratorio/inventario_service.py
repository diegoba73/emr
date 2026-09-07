"""Servicio de inventario LIMS (FEFO, alertas, egresos)."""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from laboratorio.models_inventario import (
    ConsumoInsumoExamen,
    InsumoLab,
    LoteInsumo,
    MovimientoStock,
)

logger = logging.getLogger(__name__)


def _strict() -> bool:
    return bool(getattr(settings, "LAB_INVENTARIO_STRICT", False))


def stock_insumo(insumo: InsumoLab) -> int:
    return (
        LoteInsumo.objects.filter(insumo=insumo, activo=True).aggregate(t=Sum("cantidad"))["t"]
        or 0
    )


def _unidades_a_egresar(cantidad: Decimal | int | float) -> int:
    """Stock es entero: redondeo hacia arriba de la receta (mín. 1 si > 0)."""
    d = Decimal(str(cantidad))
    if d <= 0:
        return 0
    return max(1, int(math.ceil(float(d))))


@transaction.atomic
def registrar_ingreso(
    *,
    lote: LoteInsumo,
    cantidad: int,
    user=None,
    motivo: str = "",
) -> MovimientoStock:
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser positiva.")
    LoteInsumo.objects.filter(pk=lote.pk).update(cantidad=F("cantidad") + cantidad)
    lote.refresh_from_db()
    return MovimientoStock.objects.create(
        tipo=MovimientoStock.Tipo.INGRESO,
        lote=lote,
        cantidad=cantidad,
        motivo=motivo or "Ingreso de stock",
        usuario=user,
    )


@transaction.atomic
def _egresar_de_insumo(
    insumo: InsumoLab,
    cantidad: int,
    *,
    user=None,
    motivo: str = "",
    muestra_id: int | None = None,
    siembra_id: int | None = None,
    resultado_id: int | None = None,
) -> dict[str, Any]:
    if cantidad <= 0:
        return {"ok": True, "movimientos": [], "warning": None}

    lotes = list(
        LoteInsumo.objects.select_for_update()
        .filter(insumo=insumo, activo=True, cantidad__gt=0)
        .order_by(F("fecha_vencimiento").asc(nulls_last=True), "id")
    )
    disponible = sum(l.cantidad for l in lotes)
    if disponible < cantidad:
        msg = (
            f"Stock insuficiente de {insumo.codigo}: hay {disponible}, se requieren {cantidad}."
        )
        if _strict():
            raise ValidationError(msg)
        logger.warning("inventario soft: %s", msg)
        return {"ok": False, "movimientos": [], "warning": msg}

    restante = cantidad
    movimientos: list[MovimientoStock] = []
    for lote in lotes:
        if restante <= 0:
            break
        take = min(lote.cantidad, restante)
        lote.cantidad -= take
        lote.save(update_fields=["cantidad", "updated_at"])
        mov = MovimientoStock.objects.create(
            tipo=MovimientoStock.Tipo.EGRESO,
            lote=lote,
            cantidad=take,
            motivo=motivo or "Egreso operativo",
            usuario=user,
            muestra_id=muestra_id,
            siembra_id=siembra_id,
            resultado_id=resultado_id,
        )
        movimientos.append(mov)
        restante -= take
    return {"ok": True, "movimientos": movimientos, "warning": None}


def egresar_por_contenedor(
    tipo_contenedor_id: int,
    cantidad: int = 1,
    *,
    user=None,
    muestra_id: int | None = None,
    motivo: str = "Egreso por toma/recepción de muestra",
) -> dict[str, Any]:
    insumo = (
        InsumoLab.objects.filter(
            tipo_contenedor_id=tipo_contenedor_id,
            activo=True,
            tipo=InsumoLab.Tipo.TUBO,
        )
        .order_by("id")
        .first()
    )
    if not insumo:
        return {"ok": True, "movimientos": [], "warning": None}
    return _egresar_de_insumo(
        insumo,
        cantidad,
        user=user,
        motivo=motivo,
        muestra_id=muestra_id,
    )


def egresar_medio(
    medio_id: int,
    cantidad: int = 1,
    *,
    user=None,
    siembra_id: int | None = None,
    motivo: str = "Egreso por siembra microbiológica",
) -> dict[str, Any]:
    insumo = (
        InsumoLab.objects.filter(
            medio_cultivo_id=medio_id,
            activo=True,
            tipo=InsumoLab.Tipo.MEDIO,
        )
        .order_by("id")
        .first()
    )
    if not insumo:
        return {"ok": True, "movimientos": [], "warning": None}
    return _egresar_de_insumo(
        insumo,
        cantidad,
        user=user,
        motivo=motivo,
        siembra_id=siembra_id,
    )


def egresar_por_resultado(resultado, *, user=None) -> dict[str, Any]:
    """Descuenta recetas activas del tipo_examen (FEFO). Soft si falta stock.

    Idempotente: no vuelve a egresar el mismo (resultado_id, insumo).
    """
    tipo_examen_id = getattr(resultado, "tipo_examen_id", None)
    resultado_id = getattr(resultado, "pk", None)
    if not tipo_examen_id or not resultado_id:
        return {"ok": True, "movimientos": [], "warnings": [], "skipped": True}

    recetas = list(
        ConsumoInsumoExamen.objects.filter(
            tipo_examen_id=tipo_examen_id,
            activo=True,
            insumo__activo=True,
        ).select_related("insumo")
    )
    if not recetas:
        return {"ok": True, "movimientos": [], "warnings": [], "skipped": True}

    movimientos: list[MovimientoStock] = []
    warnings: list[str] = []
    codigo_ex = getattr(getattr(resultado, "tipo_examen", None), "codigo", None) or tipo_examen_id

    for receta in recetas:
        ya = MovimientoStock.objects.filter(
            tipo=MovimientoStock.Tipo.EGRESO,
            resultado_id=resultado_id,
            lote__insumo_id=receta.insumo_id,
        ).exists()
        if ya:
            continue
        qty = _unidades_a_egresar(receta.cantidad_por_determinacion)
        if qty <= 0:
            continue
        motivo = f"Consumo determinación {codigo_ex}"
        if receta.rol:
            motivo = f"{motivo} ({receta.rol})"
        result = _egresar_de_insumo(
            receta.insumo,
            qty,
            user=user,
            motivo=motivo,
            resultado_id=resultado_id,
        )
        movimientos.extend(result.get("movimientos") or [])
        if result.get("warning"):
            warnings.append(result["warning"])

    return {
        "ok": not warnings,
        "movimientos": movimientos,
        "warnings": warnings,
        "skipped": False,
    }


def _consumo_egresos_desde(insumo_id: int, desde) -> int:
    return (
        MovimientoStock.objects.filter(
            tipo=MovimientoStock.Tipo.EGRESO,
            lote__insumo_id=insumo_id,
            created_at__gte=desde,
        ).aggregate(t=Sum("cantidad"))["t"]
        or 0
    )


def alertas(*, dias_vencimiento: int = 30, dias_proyeccion: int = 14) -> dict[str, Any]:
    hoy = timezone.localdate()
    ahora = timezone.now()
    limite = hoy + timedelta(days=dias_vencimiento)
    desde_7 = ahora - timedelta(days=7)
    desde_30 = ahora - timedelta(days=30)

    bajo_minimo = []
    pedidos = []
    for insumo in InsumoLab.objects.filter(activo=True).select_related("equipo"):
        actual = stock_insumo(insumo)
        cons_7 = _consumo_egresos_desde(insumo.id, desde_7)
        cons_30 = _consumo_egresos_desde(insumo.id, desde_30)
        sugerido = max(0, insumo.stock_min - actual)
        ritmo_diario = cons_30 / 30.0 if cons_30 else 0.0
        dias_restantes_stock = (
            int(actual / ritmo_diario) if ritmo_diario > 0 else None
        )
        ritmo_alto = bool(
            dias_restantes_stock is not None and dias_restantes_stock <= dias_proyeccion
        )
        if sugerido > 0 or ritmo_alto:
            pedidos.append(
                {
                    "insumo_id": insumo.id,
                    "codigo": insumo.codigo,
                    "nombre": insumo.nombre,
                    "tipo": insumo.tipo,
                    "unidad": insumo.unidad,
                    "proveedor": insumo.proveedor or "",
                    "canal_analizador": insumo.canal_analizador or "",
                    "composicion": insumo.composicion or "",
                    "equipo_codigo": (
                        insumo.equipo.codigo if getattr(insumo, "equipo_id", None) else None
                    ),
                    "stock_actual": actual,
                    "stock_min": insumo.stock_min,
                    "consumo_7d": cons_7,
                    "consumo_30d": cons_30,
                    "cantidad_sugerida": max(sugerido, cons_7 if ritmo_alto else 0),
                    "ritmo_alto": ritmo_alto,
                    "dias_restantes_stock": dias_restantes_stock,
                }
            )
        if actual < insumo.stock_min:
            bajo_minimo.append(
                {
                    "insumo_id": insumo.id,
                    "codigo": insumo.codigo,
                    "nombre": insumo.nombre,
                    "stock_actual": actual,
                    "stock_min": insumo.stock_min,
                    "unidad": insumo.unidad,
                    "proveedor": insumo.proveedor or "",
                    "canal_analizador": insumo.canal_analizador or "",
                    "consumo_30d": cons_30,
                    "cantidad_sugerida": sugerido,
                }
            )

    por_vencer = []
    for lote in LoteInsumo.objects.filter(
        activo=True,
        cantidad__gt=0,
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__lte=limite,
    ).select_related("insumo"):
        fv: date = lote.fecha_vencimiento
        por_vencer.append(
            {
                "lote_id": lote.id,
                "codigo_lote": lote.codigo_lote,
                "insumo_codigo": lote.insumo.codigo,
                "insumo_nombre": lote.insumo.nombre,
                "cantidad": lote.cantidad,
                "fecha_vencimiento": fv.isoformat(),
                "dias_restantes": (fv - hoy).days,
                "canal_analizador": lote.insumo.canal_analizador or "",
                "proveedor": lote.insumo.proveedor or "",
            }
        )
    return {
        "bajo_minimo": bajo_minimo,
        "por_vencer": por_vencer,
        "pedidos": pedidos,
    }
