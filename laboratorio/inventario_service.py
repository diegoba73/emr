"""Servicio de inventario LIMS (FEFO, alertas, egresos)."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from laboratorio.models_inventario import InsumoLab, LoteInsumo, MovimientoStock

logger = logging.getLogger(__name__)


def _strict() -> bool:
    return bool(getattr(settings, "LAB_INVENTARIO_STRICT", False))


def stock_insumo(insumo: InsumoLab) -> int:
    return (
        LoteInsumo.objects.filter(insumo=insumo, activo=True).aggregate(t=Sum("cantidad"))["t"]
        or 0
    )


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


def alertas(*, dias_vencimiento: int = 30) -> dict[str, Any]:
    hoy = timezone.localdate()
    limite = hoy + timedelta(days=dias_vencimiento)
    bajo_minimo = []
    for insumo in InsumoLab.objects.filter(activo=True):
        actual = stock_insumo(insumo)
        if actual < insumo.stock_min:
            bajo_minimo.append(
                {
                    "insumo_id": insumo.id,
                    "codigo": insumo.codigo,
                    "nombre": insumo.nombre,
                    "stock_actual": actual,
                    "stock_min": insumo.stock_min,
                    "unidad": insumo.unidad,
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
            }
        )
    return {"bajo_minimo": bajo_minimo, "por_vencer": por_vencer}
