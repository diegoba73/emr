"""
Analítica poblacional agregada de resultados (sin PHI).

Default de ventana superior: 2026-09-29 (corpus importado LabWin a corregir).
Solo lectura; no muta ResultadoExamen.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from statistics import median
from typing import Any

from django.utils import timezone

from laboratorio.labwin_firebird_scope import DEFAULT_SCALE_UNTIL
from laboratorio.models import ResultadoExamen


def _parse_date(raw: str | None, default: date | None) -> date | None:
    if raw is None or str(raw).strip() == "":
        return default
    return date.fromisoformat(str(raw).strip())


def _day_start(d: date) -> datetime:
    dt = datetime.combine(d, time.min)
    if timezone.is_aware(timezone.now()):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _day_end(d: date) -> datetime:
    dt = datetime.combine(d, time.max)
    if timezone.is_aware(timezone.now()):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _percentile(sorted_vals: list[Decimal], p: float) -> Decimal | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * Decimal(str(k - f))


def _histograma(valores: list[Decimal], bins: int = 8) -> list[dict[str, Any]]:
    if not valores or bins < 2:
        return []
    vmin = min(valores)
    vmax = max(valores)
    if vmin == vmax:
        return [{"desde": str(vmin), "hasta": str(vmax), "n": len(valores)}]
    width = (vmax - vmin) / Decimal(bins)
    counts = [0] * bins
    for v in valores:
        idx = int((v - vmin) / width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1
    out = []
    for i, n in enumerate(counts):
        desde = vmin + width * i
        hasta = vmin + width * (i + 1) if i < bins - 1 else vmax
        out.append({"desde": str(desde), "hasta": str(hasta), "n": n})
    return out


def analytics_analitos(
    *,
    desde: date | None = None,
    hasta: date | None = None,
    codigo: str | None = None,
    include_histogram: bool = True,
) -> dict[str, Any]:
    """
    Agrega por código de examen en la ventana de fechas de solicitud.

    ``hasta`` default = DEFAULT_SCALE_UNTIL (2026-09-29).
    """
    hasta_d = hasta or DEFAULT_SCALE_UNTIL
    desde_d = desde

    qs = (
        ResultadoExamen.objects.filter(
            solicitud__fecha_solicitud__lte=_day_end(hasta_d),
        )
        .exclude(valor_obtenido="")
        .select_related("tipo_examen", "solicitud")
    )
    if desde_d is not None:
        qs = qs.filter(solicitud__fecha_solicitud__gte=_day_start(desde_d))

    codigo_u = (codigo or "").strip().upper()
    if codigo_u:
        qs = qs.filter(tipo_examen__codigo__iexact=codigo_u)

    # Tope defensivo de filas (agregados; sin PHI en salida)
    rows = list(qs[:50000])

    by_code: dict[str, dict[str, Any]] = {}
    for r in rows:
        te = r.tipo_examen
        code = (getattr(te, "codigo", None) or "").strip().upper()
        if not code:
            continue
        bucket = by_code.setdefault(
            code,
            {
                "codigo": code,
                "nombre": (getattr(te, "nombre", None) or "").strip(),
                "n": 0,
                "n_labwin": 0,
                "n_nativo": 0,
                "n_patologico": 0,
                "n_critico": 0,
                "valores": [],
            },
        )
        bucket["n"] += 1
        num = getattr(r.solicitud, "numero", "") or ""
        if str(num).startswith("LW-"):
            bucket["n_labwin"] += 1
        else:
            bucket["n_nativo"] += 1
        if r.es_patologico:
            bucket["n_patologico"] += 1
        if r.es_critico:
            bucket["n_critico"] += 1
        if r.valor_numerico is not None:
            bucket["valores"].append(r.valor_numerico)

    analitos: list[dict[str, Any]] = []
    for code, b in sorted(by_code.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        vals: list[Decimal] = sorted(b["valores"])
        n = b["n"]
        item: dict[str, Any] = {
            "codigo": code,
            "nombre": b["nombre"],
            "n": n,
            "n_labwin": b["n_labwin"],
            "n_nativo": b["n_nativo"],
            "pct_fuera_rango": round(100.0 * b["n_patologico"] / n, 2) if n else 0.0,
            "pct_critico": round(100.0 * b["n_critico"] / n, 2) if n else 0.0,
            "n_numericos": len(vals),
            "mediana": str(median(vals)) if vals else None,
            "p25": str(_percentile(vals, 0.25)) if vals else None,
            "p75": str(_percentile(vals, 0.75)) if vals else None,
        }
        if include_histogram and vals:
            item["histograma"] = _histograma(vals)
        analitos.append(item)

    # Si no filtró por código, devolver top 40 por N
    if not codigo_u:
        analitos = analitos[:40]

    return {
        "desde": desde_d.isoformat() if desde_d else None,
        "hasta": hasta_d.isoformat(),
        "codigo_filtro": codigo_u or None,
        "total_resultados": sum(a["n"] for a in analitos),
        "analitos": analitos,
        "marcado_agregado": True,
        "sin_phi": True,
    }


def parse_analytics_query(params) -> dict[str, Any]:
    """Parsea query params DRF/Django QueryDict."""
    desde = _parse_date(params.get("desde"), None)
    hasta = _parse_date(params.get("hasta"), DEFAULT_SCALE_UNTIL)
    codigo = (params.get("codigo") or "").strip() or None
    hist_raw = str(params.get("histograma", "true")).lower()
    include_histogram = hist_raw in ("1", "true", "yes")
    return {
        "desde": desde,
        "hasta": hasta,
        "codigo": codigo,
        "include_histogram": include_histogram,
    }
