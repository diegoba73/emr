"""
B4.1 — Resultados clínicos estructurados: unidades, rangos, críticos y snapshots.

Reglas básicas (sin edad/sexo ni Westgard):
- ``valor_obtenido`` sigue siendo el valor principal compatible (pendiente si vacío).
- ``valor_numerico`` opcional para interpretación estructurada.
- Snapshots copian referencia del catálogo al momento de la carga.
- ``es_patologico`` / ``es_critico`` se calculan si hay datos suficientes; si no, respeta payload explícito.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"Valor numérico inválido: {value!r}")


def calcular_es_patologico(
    valor_numerico: Decimal | None,
    rango_min: Decimal | None,
    rango_max: Decimal | None,
) -> bool | None:
    """Fuera de rango estructurado. None si no hay datos para calcular."""
    if valor_numerico is None:
        return None
    if rango_min is None and rango_max is None:
        return None
    if rango_min is not None and valor_numerico < rango_min:
        return True
    if rango_max is not None and valor_numerico > rango_max:
        return True
    if rango_min is not None or rango_max is not None:
        return False
    return None


def calcular_es_critico(
    valor_numerico: Decimal | None,
    critico_min: Decimal | None,
    critico_max: Decimal | None,
) -> bool | None:
    """Fuera de umbral crítico. None si no hay umbrales para calcular."""
    if valor_numerico is None:
        return None
    if critico_min is None and critico_max is None:
        return None
    if critico_min is not None and valor_numerico <= critico_min:
        return True
    if critico_max is not None and valor_numerico >= critico_max:
        return True
    return False


def _rango_referencia_snapshot_texto(tipo_examen) -> str:
    texto = (tipo_examen.rango_referencia_texto or "").strip()
    if texto:
        return texto
    parts = []
    if tipo_examen.rango_min is not None:
        parts.append(str(tipo_examen.rango_min))
    if tipo_examen.rango_max is not None:
        if parts:
            parts.append("-")
        parts.append(str(tipo_examen.rango_max))
    unidad = (tipo_examen.unidad_default or "").strip()
    base = "".join(parts) if parts else ""
    if base and unidad:
        return f"{base} {unidad}"
    return base


def aplicar_snapshots_desde_tipo_examen(resultado, tipo_examen) -> None:
    """Copia unidad/rangos/críticos del catálogo al resultado (momento de carga)."""
    resultado.rango_referencia_snapshot = _rango_referencia_snapshot_texto(tipo_examen)
    resultado.rango_min_snapshot = tipo_examen.rango_min
    resultado.rango_max_snapshot = tipo_examen.rango_max
    resultado.valor_critico_min_snapshot = tipo_examen.valor_critico_min
    resultado.valor_critico_max_snapshot = tipo_examen.valor_critico_max


def aplicar_carga_estructurada(resultado, tipo_examen, item: dict[str, Any]) -> dict[str, Any]:
    """
    Aplica campos estructurados desde un ítem de ``cargar-resultados``.

    Retorna metadata de auditoría con valores anterior/nuevo (sin PHI).
    """
    valor_anterior = (resultado.valor_obtenido or "").strip()
    valor_numerico_anterior = resultado.valor_numerico
    audit: dict[str, Any] = {
        "tipo_examen_id": tipo_examen.pk,
        "valor_anterior_presente": bool(valor_anterior),
        "valor_nuevo_presente": None,
        "valor_numerico_anterior_presente": valor_numerico_anterior is not None,
        "valor_numerico_nuevo_presente": None,
        "es_patologico_anterior": resultado.es_patologico,
        "es_patologico_nuevo": None,
        "es_critico_anterior": resultado.es_critico,
        "es_critico_nuevo": None,
    }

    valor_texto = item.get("valor")
    if valor_texto is None and "valor_obtenido" in item:
        valor_texto = item.get("valor_obtenido")
    if valor_texto is not None:
        resultado.valor_obtenido = str(valor_texto)

    valor_numerico_raw = item.get("valor_numerico")
    valor_numerico: Decimal | None = None
    if valor_numerico_raw is not None and valor_numerico_raw != "":
        valor_numerico = _to_decimal(valor_numerico_raw)
        resultado.valor_numerico = valor_numerico
        if not (resultado.valor_obtenido or "").strip():
            resultado.valor_obtenido = str(valor_numerico)
    elif "valor_numerico" in item and valor_numerico_raw in (None, ""):
        resultado.valor_numerico = None

    unidad_payload = item.get("unidad")
    if unidad_payload is not None and str(unidad_payload).strip():
        resultado.unidad = str(unidad_payload).strip()
    elif not (resultado.unidad or "").strip() and (tipo_examen.unidad_default or "").strip():
        resultado.unidad = tipo_examen.unidad_default.strip()

    aplicar_snapshots_desde_tipo_examen(resultado, tipo_examen)

    rango_min = resultado.rango_min_snapshot
    rango_max = resultado.rango_max_snapshot
    crit_min = resultado.valor_critico_min_snapshot
    crit_max = resultado.valor_critico_max_snapshot

    pat_calc = calcular_es_patologico(valor_numerico, rango_min, rango_max)
    crit_calc = calcular_es_critico(valor_numerico, crit_min, crit_max)

    if pat_calc is not None:
        resultado.es_patologico = pat_calc
    else:
        resultado.es_patologico = bool(item.get("es_patologico", False))

    if crit_calc is not None:
        resultado.es_critico = crit_calc
    else:
        resultado.es_critico = bool(item.get("es_critico", False))

    if item.get("observaciones"):
        resultado.observaciones = item["observaciones"]

    audit["valor_nuevo_presente"] = bool((resultado.valor_obtenido or "").strip())
    audit["valor_numerico_nuevo_presente"] = resultado.valor_numerico is not None
    audit["es_patologico_nuevo"] = resultado.es_patologico
    audit["es_critico_nuevo"] = resultado.es_critico
    return audit
