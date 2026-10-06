"""
Sugerencia de interpretación clínica de una orden LIMS.

MedGemma (si habilitado) o plantilla por reglas. No persiste en HC.
Sin PHI de identificación en el prompt (solo códigos, valores, rangos, alertas).
"""
from __future__ import annotations

from typing import Any

from laboratorio.analisis_longitudinal import analizar_solicitud_optimizado
from laboratorio.models import SolicitudExamen


def _plantilla_reglas(analisis: dict[str, Any]) -> dict[str, Any]:
    lineas: list[str] = []
    alertas = list(analisis.get("resumen_alertas") or [])
    fuera = []
    cambios = []
    for item in analisis.get("resultados") or []:
        codigo = item.get("tipo_examen_codigo") or "?"
        valor = item.get("valor_actual") or item.get("valor_numerico_actual") or "—"
        unidad = item.get("unidad") or ""
        ref = item.get("referencia") or {}
        desv = ref.get("desviacion")
        if (
            desv in ("bajo", "alto")
            or ref.get("es_patologico")
            or ref.get("es_critico")
            or ref.get("es_patologico_calculado")
            or ref.get("es_critico_calculado")
        ):
            fuera.append(f"{codigo}={valor} {unidad}".strip())
        var = (item.get("historial") or {}).get("variacion")
        if var in ("significativa", "brusca", "cambio_cualitativo", "cambio_valor"):
            cambios.append(f"{codigo} ({var})")

    if fuera:
        lineas.append("Fuera de rango o destacados: " + "; ".join(fuera[:20]) + ".")
    if cambios:
        lineas.append("Cambios vs historial: " + "; ".join(cambios[:15]) + ".")
    if alertas:
        # Alertas ya son texto operativo; acotar longitud
        uniq = []
        for a in alertas:
            t = str(a).strip()
            if t and t not in uniq:
                uniq.append(t)
            if len(uniq) >= 12:
                break
        if uniq:
            lineas.append("Alertas: " + " | ".join(uniq) + ".")
    if not lineas:
        lineas.append(
            "Sin hallazgos automáticos relevantes vs referencia e historial en los analitos cargados."
        )
    lineas.append(
        "Sugerencia automática — revisar con criterio clínico; no constituye diagnóstico ni informe firmado."
    )
    return {
        "texto": " ".join(lineas),
        "fuente": "reglas",
        "marcado_sugerencia": True,
        "vacio": not (fuera or cambios or alertas),
        "total_analizados": analisis.get("total_analizados") or 0,
        "total_cambios_significativos": analisis.get("total_cambios_significativos") or 0,
    }


def _build_prompt(analisis: dict[str, Any], borrador_reglas: str) -> str:
    lines = [
        "Sos un asistente clínico de laboratorio. Redactá un párrafo breve en español",
        "como sugerencia de interpretación para el médico, sin diagnóstico definitivo,",
        "sin mencionar paciente ni datos identificatorios, sin firmar ni validar.",
        "Máximo 6 oraciones. Estilo: hallazgos de laboratorio orientativos.",
        "",
        "Analitos (código, valor, ref, alertas):",
    ]
    for item in analisis.get("resultados") or []:
        codigo = item.get("tipo_examen_codigo") or "?"
        valor = item.get("valor_actual") or item.get("valor_numerico_actual") or ""
        unidad = item.get("unidad") or ""
        ref = item.get("referencia") or {}
        rmin = ref.get("rango_min") or "—"
        rmax = ref.get("rango_max") or "—"
        desv = ref.get("desviacion") or "—"
        hist = item.get("historial") or {}
        var = hist.get("variacion") or "—"
        alertas = ",".join(item.get("alertas") or []) or "—"
        crit = bool(ref.get("es_critico") or ref.get("es_critico_calculado"))
        lines.append(
            f"- {codigo}: {valor} {unidad} (ref {rmin}-{rmax}; desv={desv}; "
            f"var_hist={var}; critico={crit}; alertas={alertas})"
        )
    if borrador_reglas.strip():
        lines.append("")
        lines.append(f"Borrador heurístico (podés mejorarlo): {borrador_reglas.strip()}")
    lines.append("")
    lines.append("Respondé solo con el párrafo de sugerencia, sin markdown.")
    return "\n".join(lines)


def sugerir_interpretacion_orden(
    solicitud: SolicitudExamen,
    *,
    prefer_medgemma: bool = True,
) -> dict[str, Any]:
    """
    Orquesta análisis longitudinal + MedGemma/reglas.
    No persiste; el médico revisa en pantalla.
    """
    from laboratorio.medgemma_client import intentar_generar_texto_medgemma

    analisis = analizar_solicitud_optimizado(solicitud)
    if not analisis.get("total_analizados"):
        return {
            "texto": (
                "No hay resultados cargados para sugerir una interpretación. "
                "Cuando haya valores, se podrá generar una sugerencia."
            ),
            "fuente": "reglas",
            "marcado_sugerencia": True,
            "vacio": True,
            "total_analizados": 0,
            "total_cambios_significativos": 0,
        }

    reglas = _plantilla_reglas(analisis)
    if not prefer_medgemma:
        return reglas

    prompt = _build_prompt(analisis, reglas.get("texto") or "")
    med = intentar_generar_texto_medgemma(prompt, multilinea=True)
    if med and med.get("texto"):
        return {
            **med,
            "marcado_sugerencia": True,
            "total_analizados": analisis.get("total_analizados") or 0,
            "total_cambios_significativos": analisis.get("total_cambios_significativos") or 0,
            "vacio": False,
        }
    return reglas
