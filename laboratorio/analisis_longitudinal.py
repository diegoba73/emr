"""
Análisis longitudinal de resultados de laboratorio (Fase 1 — sin IA).

Por cada ``ResultadoExamen`` con valor cargado:
- Comparación vs rango de referencia (snapshot / catálogo).
- Comparación vs el último resultado histórico del mismo analito en el paciente.

Pensado para alimentar alertas en el LIMS y, en fases posteriores, el contexto de MedGemma.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from laboratorio.analisis_longitudinal_config import umbrales_para_codigo
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.resultados_clinicos import calcular_es_critico, calcular_es_patologico

ESTADOS_HISTORIAL_VALIDOS = ("FINALIZADO", "INFORMADO_PARCIAL")


def _decimal_a_json(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _fecha_a_json(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            return value.isoformat()
        return value.isoformat()
    return value.isoformat()


def resultado_tiene_valor(resultado: ResultadoExamen) -> bool:
    return bool((resultado.valor_obtenido or "").strip())


def _desviacion_referencia(
    valor_numerico: Decimal | None,
    rango_min: Decimal | None,
    rango_max: Decimal | None,
) -> str | None:
    if valor_numerico is None:
        return None
    if rango_min is not None and valor_numerico < rango_min:
        return "bajo"
    if rango_max is not None and valor_numerico > rango_max:
        return "alto"
    if rango_min is not None or rango_max is not None:
        return "normal"
    return None


def _analisis_referencia(resultado: ResultadoExamen) -> dict[str, Any]:
    valor_numerico = resultado.valor_numerico
    rango_min = resultado.rango_min_snapshot
    rango_max = resultado.rango_max_snapshot
    crit_min = resultado.valor_critico_min_snapshot
    crit_max = resultado.valor_critico_max_snapshot

    pat_calc = calcular_es_patologico(valor_numerico, rango_min, rango_max)
    crit_calc = calcular_es_critico(valor_numerico, crit_min, crit_max)

    en_rango: bool | None = None
    if pat_calc is not None:
        en_rango = not pat_calc

    return {
        "tiene_rango": rango_min is not None or rango_max is not None,
        "en_rango": en_rango,
        "es_patologico": bool(resultado.es_patologico),
        "es_critico": bool(resultado.es_critico),
        "es_patologico_calculado": pat_calc,
        "es_critico_calculado": crit_calc,
        "desviacion": _desviacion_referencia(valor_numerico, rango_min, rango_max),
        "rango_texto": (resultado.rango_referencia_snapshot or "").strip(),
        "rango_min": _decimal_a_json(rango_min),
        "rango_max": _decimal_a_json(rango_max),
    }


def buscar_resultado_historico(
    *,
    paciente_id: int,
    tipo_examen_id: int,
    excluir_solicitud_id: int,
    antes_de: datetime | None = None,
) -> ResultadoExamen | None:
    """
    Último resultado previo del mismo analito para el paciente.

    Solo considera órdenes informadas (finalizadas o parciales) con valor cargado.
    """
    qs = (
        ResultadoExamen.objects.filter(
            solicitud__paciente_id=paciente_id,
            tipo_examen_id=tipo_examen_id,
            solicitud__estado__in=ESTADOS_HISTORIAL_VALIDOS,
        )
        .exclude(solicitud_id=excluir_solicitud_id)
        .exclude(valor_obtenido="")
        .select_related("solicitud", "tipo_examen")
        .order_by("-solicitud__fecha_solicitud", "-fecha_validacion", "-id")
    )
    if antes_de is not None:
        qs = qs.filter(solicitud__fecha_solicitud__lt=antes_de)
    return qs.first()


def _calcular_delta_porcentual(
    actual: Decimal,
    anterior: Decimal,
) -> Decimal | None:
    if anterior == 0:
        return None
    try:
        return ((actual - anterior) / abs(anterior)) * Decimal("100")
    except (InvalidOperation, ZeroDivisionError):
        return None


def _dias_entre(fecha_anterior: datetime | None, fecha_actual: datetime | None) -> int | None:
    if fecha_anterior is None or fecha_actual is None:
        return None
    fa = fecha_anterior.date() if isinstance(fecha_anterior, datetime) else fecha_anterior
    fb = fecha_actual.date() if isinstance(fecha_actual, datetime) else fecha_actual
    return (fb - fa).days


def _clasificar_variacion(delta_pct: Decimal | None, codigo: str) -> str:
    if delta_pct is None:
        return "sin_comparacion_numerica"
    umbrales = umbrales_para_codigo(codigo)
    abs_pct = abs(delta_pct)
    if abs_pct < Decimal(str(umbrales["estable"])):
        return "estable"
    if abs_pct < Decimal(str(umbrales["moderada"])):
        return "moderada"
    if abs_pct < Decimal(str(umbrales["brusca"])):
        return "significativa"
    return "brusca"


def _normalizar_texto(valor: str | None) -> str:
    return (valor or "").strip().lower()


def _analisis_historial(
    resultado: ResultadoExamen,
    historico: ResultadoExamen | None,
    *,
    fecha_referencia: datetime | None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "tiene_historial": historico is not None,
        "valor_anterior": None,
        "valor_numerico_anterior": None,
        "unidad_anterior": None,
        "fecha_anterior": None,
        "solicitud_anterior_id": None,
        "solicitud_anterior_numero": None,
        "dias_desde_anterior": None,
        "delta_absoluto": None,
        "delta_porcentual": None,
        "cambio_cualitativo": None,
        "variacion": "sin_historial",
    }
    if historico is None:
        return base

    sol_ant = historico.solicitud
    fecha_ant = historico.fecha_validacion or sol_ant.fecha_solicitud
    base.update(
        {
            "valor_anterior": historico.valor_obtenido,
            "valor_numerico_anterior": _decimal_a_json(historico.valor_numerico),
            "unidad_anterior": (historico.unidad or "").strip() or None,
            "fecha_anterior": _fecha_a_json(fecha_ant),
            "solicitud_anterior_id": sol_ant.pk,
            "solicitud_anterior_numero": sol_ant.numero,
            "dias_desde_anterior": _dias_entre(fecha_ant, fecha_referencia),
        }
    )

    tipo_resultado = getattr(resultado.tipo_examen, "tipo_resultado", "TEXTO") or "TEXTO"
    codigo = getattr(resultado.tipo_examen, "codigo", "") or ""

    if tipo_resultado == "CUALITATIVO" or (
        tipo_resultado == "TEXTO" and resultado.valor_numerico is None
    ):
        cambio = _normalizar_texto(resultado.valor_obtenido) != _normalizar_texto(
            historico.valor_obtenido
        )
        base["cambio_cualitativo"] = cambio
        base["variacion"] = "cambio_cualitativo" if cambio else "estable"
        return base

    actual = resultado.valor_numerico
    anterior = historico.valor_numerico
    if actual is not None and anterior is not None:
        delta_abs = actual - anterior
        delta_pct = _calcular_delta_porcentual(actual, anterior)
        base["delta_absoluto"] = _decimal_a_json(delta_abs)
        base["delta_porcentual"] = _decimal_a_json(
            delta_pct.quantize(Decimal("0.01")) if delta_pct is not None else None
        )
        base["variacion"] = _clasificar_variacion(delta_pct, codigo)
    else:
        cambio_texto = _normalizar_texto(resultado.valor_obtenido) != _normalizar_texto(
            historico.valor_obtenido
        )
        if cambio_texto:
            base["cambio_cualitativo"] = True
            base["variacion"] = "cambio_valor"
        else:
            base["variacion"] = "estable"

    return base


def _generar_alertas(
    *,
    codigo: str,
    nombre: str,
    referencia: dict[str, Any],
    historial: dict[str, Any],
    valor_actual: str,
) -> list[str]:
    alertas: list[str] = []
    label = f"{nombre} ({codigo})" if codigo else nombre

    if referencia.get("es_critico"):
        alertas.append(f"{label}: valor crítico")
    elif referencia.get("es_patologico"):
        desv = referencia.get("desviacion")
        if desv == "bajo":
            alertas.append(f"{label}: por debajo del rango de referencia")
        elif desv == "alto":
            alertas.append(f"{label}: por encima del rango de referencia")
        else:
            alertas.append(f"{label}: fuera del rango de referencia")

    if not historial.get("tiene_historial"):
        return alertas

    variacion = historial.get("variacion")
    if variacion == "brusca":
        prev = historial.get("valor_anterior") or historial.get("valor_numerico_anterior")
        delta = historial.get("delta_porcentual")
        dias = historial.get("dias_desde_anterior")
        extra = f" ({delta}% en {dias} días)" if delta and dias is not None else ""
        alertas.append(
            f"{label}: cambio brusco respecto al historial ({prev} → {valor_actual}{extra})"
        )
    elif variacion == "significativa":
        delta = historial.get("delta_porcentual")
        if delta:
            alertas.append(
                f"{label}: variación significativa vs historial ({delta}%)"
            )
    elif variacion == "cambio_cualitativo":
        prev = historial.get("valor_anterior")
        alertas.append(
            f"{label}: cambio cualitativo ({prev} → {valor_actual})"
        )
    elif variacion == "cambio_valor":
        prev = historial.get("valor_anterior")
        alertas.append(f"{label}: valor distinto al anterior ({prev} → {valor_actual})")

    return alertas


def analizar_resultado(
    resultado: ResultadoExamen,
    *,
    historico: ResultadoExamen | None = None,
    fecha_referencia: datetime | None = None,
) -> dict[str, Any] | None:
    """Analiza un resultado individual. Retorna ``None`` si no tiene valor cargado."""
    if not resultado_tiene_valor(resultado):
        return None

    solicitud = resultado.solicitud
    tipo = resultado.tipo_examen
    codigo = (tipo.codigo or "").strip().upper() if tipo else ""
    nombre = (tipo.nombre or "").strip() if tipo else ""

    if historico is None:
        historico = buscar_resultado_historico(
            paciente_id=solicitud.paciente_id,
            tipo_examen_id=resultado.tipo_examen_id,
            excluir_solicitud_id=solicitud.pk,
            antes_de=fecha_referencia or solicitud.fecha_solicitud,
        )

    ref = _analisis_referencia(resultado)
    hist = _analisis_historial(
        resultado,
        historico,
        fecha_referencia=fecha_referencia or solicitud.fecha_solicitud,
    )
    alertas = _generar_alertas(
        codigo=codigo,
        nombre=nombre,
        referencia=ref,
        historial=hist,
        valor_actual=resultado.valor_obtenido,
    )

    return {
        "resultado_id": resultado.pk,
        "tipo_examen_id": resultado.tipo_examen_id,
        "tipo_examen_codigo": codigo,
        "tipo_examen_nombre": nombre,
        "tipo_resultado": getattr(tipo, "tipo_resultado", None),
        "valor_actual": resultado.valor_obtenido,
        "valor_numerico_actual": _decimal_a_json(resultado.valor_numerico),
        "unidad": (resultado.unidad or "").strip() or None,
        "referencia": ref,
        "historial": hist,
        "alertas": alertas,
    }


def analizar_solicitud(
    solicitud: SolicitudExamen,
    *,
    resultado_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Analiza todos los resultados con valor de una orden (o un subconjunto por id).
    """
    qs = solicitud.resultados.select_related("tipo_examen", "solicitud").all()
    if resultado_ids is not None:
        qs = qs.filter(pk__in=resultado_ids)

    items: list[dict[str, Any]] = []
    todas_alertas: list[str] = []
    cambios_significativos = 0
    con_historial = 0

    for resultado in qs:
        if not resultado_tiene_valor(resultado):
            continue
        item = analizar_resultado(resultado)
        if item is None:
            continue
        items.append(item)
        todas_alertas.extend(item["alertas"])
        if item["historial"].get("tiene_historial"):
            con_historial += 1
        if item["historial"].get("variacion") in (
            "significativa",
            "brusca",
            "cambio_cualitativo",
            "cambio_valor",
        ):
            cambios_significativos += 1

    return {
        "solicitud_id": solicitud.pk,
        "solicitud_numero": solicitud.numero,
        "paciente_id": solicitud.paciente_id,
        "fecha_solicitud": _fecha_a_json(solicitud.fecha_solicitud),
        "estado_solicitud": solicitud.estado,
        "resultados": items,
        "resumen_alertas": todas_alertas,
        "total_analizados": len(items),
        "total_con_historial": con_historial,
        "total_cambios_significativos": cambios_significativos,
    }


def precargar_historicos_paciente(
    paciente_id: int,
    tipo_examen_ids: list[int],
    excluir_solicitud_id: int,
    antes_de: datetime,
) -> dict[int, ResultadoExamen | None]:
    """
    Precarga en una consulta los últimos históricos por tipo de examen (optimización N+1).
    """
    if not tipo_examen_ids:
        return {}

    historicos: dict[int, ResultadoExamen | None] = {tid: None for tid in tipo_examen_ids}
    qs = (
        ResultadoExamen.objects.filter(
            solicitud__paciente_id=paciente_id,
            tipo_examen_id__in=tipo_examen_ids,
            solicitud__estado__in=ESTADOS_HISTORIAL_VALIDOS,
            solicitud__fecha_solicitud__lt=antes_de,
        )
        .exclude(solicitud_id=excluir_solicitud_id)
        .exclude(valor_obtenido="")
        .select_related("solicitud", "tipo_examen")
        .order_by("tipo_examen_id", "-solicitud__fecha_solicitud", "-fecha_validacion", "-id")
    )
    for res in qs:
        tid = res.tipo_examen_id
        if historicos.get(tid) is None:
            historicos[tid] = res
    return historicos


def analizar_solicitud_optimizado(solicitud: SolicitudExamen) -> dict[str, Any]:
    """Variante con precarga de históricos para listados grandes."""
    resultados = list(
        solicitud.resultados.select_related("tipo_examen", "solicitud").all()
    )
    con_valor = [r for r in resultados if resultado_tiene_valor(r)]
    tipo_ids = list({r.tipo_examen_id for r in con_valor})
    historicos = precargar_historicos_paciente(
        solicitud.paciente_id,
        tipo_ids,
        solicitud.pk,
        solicitud.fecha_solicitud,
    )

    items: list[dict[str, Any]] = []
    todas_alertas: list[str] = []
    cambios_significativos = 0
    con_historial = 0

    for resultado in con_valor:
        item = analizar_resultado(
            resultado,
            historico=historicos.get(resultado.tipo_examen_id),
            fecha_referencia=solicitud.fecha_solicitud,
        )
        if item is None:
            continue
        items.append(item)
        todas_alertas.extend(item["alertas"])
        if item["historial"].get("tiene_historial"):
            con_historial += 1
        if item["historial"].get("variacion") in (
            "significativa",
            "brusca",
            "cambio_cualitativo",
            "cambio_valor",
        ):
            cambios_significativos += 1

    return {
        "solicitud_id": solicitud.pk,
        "solicitud_numero": solicitud.numero,
        "paciente_id": solicitud.paciente_id,
        "fecha_solicitud": _fecha_a_json(solicitud.fecha_solicitud),
        "estado_solicitud": solicitud.estado,
        "resultados": items,
        "resumen_alertas": todas_alertas,
        "total_analizados": len(items),
        "total_con_historial": con_historial,
        "total_cambios_significativos": cambios_significativos,
    }
