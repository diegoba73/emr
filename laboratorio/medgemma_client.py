"""
Cliente opcional MedGemma / Ollama para borradores de conclusión de hemograma.

Reglas (docs_synesis/reglas/ia.md):
- Solo sugerencia; no valida ni firma.
- Payload mínimo (códigos + valores + rangos); sin PHI de identificación.
- Si el servicio no está disponible, el caller usa el motor de reglas.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def medgemma_habilitado() -> bool:
    return bool(getattr(settings, "MEDGEMMA_ENABLED", False))


def _payload_analitos(
    solicitud,
    *,
    valores_borrador: dict | None = None,
) -> list[dict[str, Any]]:
    by_codigo: dict[str, dict[str, Any]] = {}
    for res in solicitud.resultados.select_related("tipo_examen").all():
        te = getattr(res, "tipo_examen", None)
        codigo = (getattr(te, "codigo", None) or "").strip().upper()
        if not codigo:
            continue
        valor = getattr(res, "valor_numerico", None)
        if valor is None or valor == "":
            valor = getattr(res, "valor_obtenido", None)
        entry = {
            "codigo": codigo,
            "valor": str(valor) if valor is not None and str(valor).strip() != "" else "",
            "unidad": (getattr(res, "unidad", None) or getattr(te, "unidad_default", None) or ""),
            "rango_min": str(getattr(res, "rango_min_snapshot", None) or ""),
            "rango_max": str(getattr(res, "rango_max_snapshot", None) or ""),
            "fuera_rango": bool(getattr(res, "es_patologico", False)),
            "critico": bool(getattr(res, "es_critico", False)),
        }
        by_codigo[codigo] = entry

    if valores_borrador:
        for codigo_raw, valor in valores_borrador.items():
            codigo = str(codigo_raw or "").strip().upper()
            if not codigo or valor is None or str(valor).strip() == "":
                continue
            base = by_codigo.get(codigo) or {
                "codigo": codigo,
                "unidad": "",
                "rango_min": "",
                "rango_max": "",
                "fuera_rango": False,
                "critico": False,
            }
            base["valor"] = str(valor)
            by_codigo[codigo] = base

    return [entry for entry in by_codigo.values() if entry.get("valor")]


def _build_prompt(analitos: list[dict[str, Any]], borrador_reglas: str) -> str:
    lines = [
        "Sos un asistente de laboratorio clínico. Redactá UNA sola frase breve en español",
        "como conclusión de hemograma (estilo informe), sin diagnóstico definitivo,",
        "sin mencionar al paciente ni datos identificatorios.",
        "Ejemplo de estilo: «Anemia normocítica normocrómica, con trombocitopenia leve y anisocitosis.»",
        "",
        "Analitos (código, valor, rango):",
    ]
    for a in analitos:
        lines.append(
            f"- {a['codigo']}: {a['valor']} {a.get('unidad') or ''} "
            f"(ref {a.get('rango_min') or '—'}-{a.get('rango_max') or '—'}; "
            f"fuera_rango={a.get('fuera_rango')}; critico={a.get('critico')})"
        )
    if borrador_reglas.strip():
        lines.append("")
        lines.append(f"Borrador heurístico de referencia (podés mejorarlo): {borrador_reglas.strip()}")
    lines.append("")
    lines.append("Respondé solo con la frase de conclusión, sin markdown ni explicación.")
    return "\n".join(lines)


def _call_ollama(prompt: str) -> str | None:
    base = (getattr(settings, "MEDGEMMA_BASE_URL", None) or "").rstrip("/")
    model = getattr(settings, "MEDGEMMA_MODEL", "medgemma-1.5") or "medgemma-1.5"
    timeout = int(getattr(settings, "MEDGEMMA_TIMEOUT_SECONDS", 30) or 30)
    if not base:
        return None

    url = f"{base}/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.info("MedGemma/Ollama no disponible: %s", exc)
        return None

    texto = (raw.get("response") or "").strip()
    if not texto:
        return None
    # Primera línea / sin comillas decorativas (hemograma); informes pueden ser multilínea
    return texto or None


def intentar_generar_texto_medgemma(prompt: str, *, multilinea: bool = False) -> dict[str, Any] | None:
    """
    Llamada genérica a MedGemma/Ollama. No envía PHI: el caller arma el prompt.
    """
    if not medgemma_habilitado():
        return None
    if not (prompt or "").strip():
        return None

    texto = _call_ollama(prompt)
    if not texto:
        return None
    if not multilinea:
        texto = texto.split("\n")[0].strip().strip('"').strip("'")
    else:
        texto = texto.strip().strip('"').strip("'")
    if not texto:
        return None

    return {
        "texto": texto,
        "fuente": "medgemma",
        "marcado_sugerencia": True,
        "modelo": getattr(settings, "MEDGEMMA_MODEL", "medgemma-1.5"),
        "vacio": False,
    }


def intentar_conclusion_medgemma(
    solicitud,
    *,
    borrador_reglas: str = "",
    valores_borrador: dict | None = None,
) -> dict[str, Any] | None:
    """
    Devuelve dict de sugerencia si MedGemma responde; None si deshabilitado o falla.
    """
    if not medgemma_habilitado():
        return None

    analitos = _payload_analitos(solicitud, valores_borrador=valores_borrador)
    if not analitos:
        return None

    prompt = _build_prompt(analitos, borrador_reglas)
    med = intentar_generar_texto_medgemma(prompt, multilinea=False)
    if not med:
        return None
    return med
