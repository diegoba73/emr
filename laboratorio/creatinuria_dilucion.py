"""
Creatininuria (CREA_U): orina diluida 1:20 en CM260.

El operador tipea el valor del equipo; en órdenes nuevas el LIMS multiplica ×20
para informar y para derivados (RAC, clearance, etc.).

Órdenes con ``fecha_solicitud`` anterior a ``CREATINURIA_DILUCION_DESDE`` no
aplican el factor (compatibilidad con resultados ya cargados).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from laboratorio.entrada_resultados import quantize_valor_numerico

CODIGO_CREATINURIA = "CREA_U"
FACTOR_DILUCION_CREATINURIA = Decimal("20")
# 2026-10-21 14:00 ART — solo órdenes creadas desde entonces.
CREATINURIA_DILUCION_DESDE = datetime(
    2026, 10, 21, 14, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires")
)


def aplica_dilucion_creatinuria(solicitud) -> bool:
    """True si la orden debe corregir CREA_U por dilución 1:20."""
    if solicitud is None:
        return False
    fecha = getattr(solicitud, "fecha_solicitud", None)
    if fecha is None:
        return False
    if timezone_is_naive(fecha):
        from django.utils import timezone as dj_tz

        fecha = dj_tz.make_aware(fecha, dj_tz.get_current_timezone())
    return fecha >= CREATINURIA_DILUCION_DESDE


def timezone_is_naive(value: datetime) -> bool:
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None


def factor_dilucion_creatinuria(solicitud) -> Decimal:
    if aplica_dilucion_creatinuria(solicitud):
        return FACTOR_DILUCION_CREATINURIA
    return Decimal("1")


def _es_creatinuria(tipo_examen) -> bool:
    codigo = (getattr(tipo_examen, "codigo", None) or "").strip().upper()
    return codigo == CODIGO_CREATINURIA


def _parse_decimal(raw: Any) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fmt_informe(value: Decimal) -> str:
    q = quantize_valor_numerico(value)
    text = format(q, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def aplicar_dilucion_creatinuria_en_item(
    tipo_examen, item: dict[str, Any], solicitud
) -> bool:
    """
    Si corresponde, multiplica valor/valor_numerico del ítem de carga ×20.

    Mutates ``item``. Retorna True si aplicó el factor.
    """
    if not _es_creatinuria(tipo_examen):
        return False
    if not aplica_dilucion_creatinuria(solicitud):
        return False

    vn = _parse_decimal(item.get("valor_numerico"))
    if vn is None:
        raw_txt = item.get("valor")
        if raw_txt is None:
            raw_txt = item.get("valor_obtenido")
        vn = _parse_decimal(raw_txt)
    if vn is None:
        return False

    clinico = quantize_valor_numerico(vn * FACTOR_DILUCION_CREATINURIA)
    texto = _fmt_informe(clinico)
    item["valor_numerico"] = clinico
    item["valor"] = texto
    item["valor_obtenido"] = texto
    return True
