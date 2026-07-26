"""
Borrador de conclusión de hemograma a partir de indicadores (Sysmex / LIMS).

No es diagnóstico clínico: genera texto sugerido para ``SolicitudExamen.observaciones``.
Índices derivados: VCM ≈ HTO/HEMATIES×10, CHCM ≈ HGB/HTO×100.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from laboratorio.catalogo_referencias_clinicas import REFERENCIAS_POR_CODIGO
from laboratorio.orden_grupos_informe import PANEL_HEMOGRAMA

# Rangos típicos adultos para índices calculados (fL / g/dL).
VCM_MIN = Decimal("80")
VCM_MAX = Decimal("100")
CHCM_MIN = Decimal("32")
CHCM_MAX = Decimal("36")

# Grados (umbrales de laboratorio de uso frecuente; sugerencia no diagnóstica).
PLAQ_LEVE_MIN = Decimal("100000")
PLAQ_MOD_MIN = Decimal("50000")

# Anemia por HGB (g/dL): leve ≥10; moderada 7–<10; severa <7.
HGB_ANEMIA_LEVE_MIN = Decimal("10")
HGB_ANEMIA_MOD_MIN = Decimal("7")

# Anisocitosis por RDW (%): leve ≤16; moderada ≤18; severa >18.
RDW_ANISO_LEVE_MAX = Decimal("16")
RDW_ANISO_MOD_MAX = Decimal("18")

# Leucocitosis (/mm³): leve ≤15000; moderada ≤25000; severa >25000.
LEU_CITOSIS_LEVE_MAX = Decimal("15000")
LEU_CITOSIS_MOD_MAX = Decimal("25000")

# Leucopenia (/mm³): leve ≥3000; moderada ≥1500; severa <1500.
LEU_PENIA_LEVE_MIN = Decimal("3000")
LEU_PENIA_MOD_MIN = Decimal("1500")


def _dec(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _ref_bounds(codigo: str, resultado=None) -> tuple[Decimal | None, Decimal | None]:
    """Preferir snapshot del resultado; si no, catálogo."""
    rmin = rmax = None
    if resultado is not None:
        rmin = _dec(getattr(resultado, "rango_min_snapshot", None))
        rmax = _dec(getattr(resultado, "rango_max_snapshot", None))
    cat = REFERENCIAS_POR_CODIGO.get(codigo) or {}
    if rmin is None:
        rmin = cat.get("rango_min")
    if rmax is None:
        rmax = cat.get("rango_max")
    return rmin, rmax


def _valores_por_codigo(
    solicitud,
    *,
    valores_borrador: dict[str, Decimal] | None = None,
) -> dict[str, tuple[Decimal, Any]]:
    """codigo -> (valor_numerico, resultado|None). El borrador pisa valores de BD."""
    out: dict[str, tuple[Decimal, Any]] = {}
    res_by_codigo: dict[str, Any] = {}
    qs = solicitud.resultados.select_related("tipo_examen").all()
    for res in qs:
        te = getattr(res, "tipo_examen", None)
        codigo = (getattr(te, "codigo", None) or "").strip().upper()
        if not codigo:
            continue
        res_by_codigo[codigo] = res
        num = _dec(getattr(res, "valor_numerico", None))
        if num is None:
            num = _dec(getattr(res, "valor_obtenido", None))
        if num is None:
            continue
        out[codigo] = (num, res)

    if valores_borrador:
        for codigo_raw, num in valores_borrador.items():
            codigo = (codigo_raw or "").strip().upper()
            if not codigo or num is None:
                continue
            out[codigo] = (num, res_by_codigo.get(codigo))
    return out


def parse_valores_borrador(raw: Any) -> dict[str, Decimal]:
    """
    Acepta ``{"HGB": "12.5", ...}`` o ``[{"codigo": "HGB", "valor": "12.5"}, ...]``.
    Ignora entradas no numéricas.
    """
    out: dict[str, Decimal] = {}
    if not raw:
        return out
    if isinstance(raw, dict):
        items = raw.items()
        for codigo, valor in items:
            num = _dec(valor)
            if num is None:
                continue
            c = str(codigo or "").strip().upper()
            if c:
                out[c] = num
        return out
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            num = _dec(item.get("valor") if "valor" in item else item.get("valor_numerico"))
            if num is None:
                continue
            c = str(item.get("codigo") or "").strip().upper()
            if c:
                out[c] = num
    return out


def solicitud_tiene_hemograma(solicitud) -> bool:
    """True si la orden incluye panel PAN_HEMO o los analitos centrales."""
    try:
        if solicitud.paneles.filter(codigo=PANEL_HEMOGRAMA).exists():
            return True
    except Exception:
        pass
    codigos = set()
    for res in solicitud.resultados.select_related("tipo_examen").all():
        te = getattr(res, "tipo_examen", None)
        c = (getattr(te, "codigo", None) or "").strip().upper()
        if c:
            codigos.add(c)
    return {"HGB", "HEMATIES", "HTO"}.issubset(codigos) or "HGB" in codigos


def _clasificar_vs_rango(valor: Decimal, rmin: Decimal | None, rmax: Decimal | None) -> str:
    if rmin is not None and valor < rmin:
        return "bajo"
    if rmax is not None and valor > rmax:
        return "alto"
    return "normal"


def _grado_trombocitopenia(plaq: Decimal) -> str:
    if plaq >= PLAQ_LEVE_MIN:
        return "leve"
    if plaq >= PLAQ_MOD_MIN:
        return "moderada"
    return "severa"


def _grado_anemia(hgb: Decimal) -> str:
    if hgb >= HGB_ANEMIA_LEVE_MIN:
        return "leve"
    if hgb >= HGB_ANEMIA_MOD_MIN:
        return "moderada"
    return "severa"


def _grado_anisocitosis(rdw: Decimal) -> str:
    if rdw <= RDW_ANISO_LEVE_MAX:
        return "leve"
    if rdw <= RDW_ANISO_MOD_MAX:
        return "moderada"
    return "severa"


def _grado_leucocitosis(leu: Decimal) -> str:
    if leu <= LEU_CITOSIS_LEVE_MAX:
        return "leve"
    if leu <= LEU_CITOSIS_MOD_MAX:
        return "moderada"
    return "severa"


def _grado_leucopenia(leu: Decimal) -> str:
    if leu >= LEU_PENIA_LEVE_MIN:
        return "leve"
    if leu >= LEU_PENIA_MOD_MIN:
        return "moderada"
    return "severa"


def _frase_anemia_morfologia(
    hgb: Decimal,
    hgb_estado: str,
    vcm: Decimal | None,
    chcm: Decimal | None,
) -> str | None:
    if hgb_estado == "normal":
        return None
    if hgb_estado == "alto":
        return "Poliglobulia / hemoglobina elevada"

    grado = _grado_anemia(hgb)
    if vcm is None or chcm is None:
        return f"Anemia {grado}"

    if vcm < VCM_MIN:
        size = "microcítica"
    elif vcm > VCM_MAX:
        size = "macrocítica"
    else:
        size = "normocítica"

    if chcm < CHCM_MIN:
        color = "hipocrómica"
    elif chcm > CHCM_MAX:
        color = "hipercrómica"
    else:
        color = "normocrómica"

    return f"Anemia {grado} {size} {color}"


def _frase_plaquetas(plaq: Decimal, estado: str) -> str | None:
    if estado == "bajo":
        grado = _grado_trombocitopenia(plaq)
        return f"trombocitopenia {grado}"
    if estado == "alto":
        return "trombocitosis"
    return None


def _frase_rdw(rdw: Decimal, estado: str) -> str | None:
    if estado == "alto":
        return f"anisocitosis {_grado_anisocitosis(rdw)}"
    return None


def _frase_leucocitos(leu: Decimal, estado: str) -> str | None:
    if estado == "bajo":
        return f"leucopenia {_grado_leucopenia(leu)}"
    if estado == "alto":
        return f"leucocitosis {_grado_leucocitosis(leu)}"
    return None


def construir_conclusion_hemograma_reglas(
    solicitud,
    *,
    valores_borrador: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Genera borrador textual a partir de resultados cargados (BD y/o borrador de pantalla).

    Returns:
        dict con ``texto``, ``fuente`` (= \"reglas\"), ``marcado_sugerencia``,
        ``detalle`` (índices usados) y ``vacio`` si no hay datos suficientes.
    """
    vals = _valores_por_codigo(solicitud, valores_borrador=valores_borrador)
    detalle: dict[str, Any] = {}
    partes_principales: list[str] = []
    extras: list[str] = []

    hgb_t = vals.get("HGB")
    rbc_t = vals.get("HEMATIES")
    hto_t = vals.get("HTO")
    rdw_t = vals.get("RDW")
    plaq_t = vals.get("PLAQ")
    leu_t = vals.get("LEUCO")
    vcm_t = vals.get("VCM")
    chcm_t = vals.get("CHCM")

    vcm = chcm = None
    if vcm_t:
        vcm = vcm_t[0]
        detalle["vcm_fl"] = str(vcm.quantize(Decimal("0.1")))
        detalle["vcm_fuente"] = "resultado"
    elif rbc_t and hto_t and rbc_t[0] > 0:
        vcm = (hto_t[0] / rbc_t[0]) * Decimal("10")
        detalle["vcm_fl"] = str(vcm.quantize(Decimal("0.1")))
        detalle["vcm_fuente"] = "calculado"
    if chcm_t:
        chcm = chcm_t[0]
        detalle["chcm_g_dl"] = str(chcm.quantize(Decimal("0.1")))
        detalle["chcm_fuente"] = "resultado"
    elif hgb_t and hto_t and hto_t[0] > 0:
        chcm = (hgb_t[0] / hto_t[0]) * Decimal("100")
        detalle["chcm_g_dl"] = str(chcm.quantize(Decimal("0.1")))
        detalle["chcm_fuente"] = "calculado"

    if hgb_t:
        hgb, res_h = hgb_t
        rmin, rmax = _ref_bounds("HGB", res_h)
        estado_h = _clasificar_vs_rango(hgb, rmin, rmax)
        detalle["hgb"] = str(hgb)
        detalle["hgb_estado"] = estado_h
        if estado_h == "bajo":
            detalle["hgb_grado"] = _grado_anemia(hgb)
        frase = _frase_anemia_morfologia(hgb, estado_h, vcm, chcm)
        if frase:
            partes_principales.append(frase)

    if plaq_t:
        plaq, res_p = plaq_t
        rmin, rmax = _ref_bounds("PLAQ", res_p)
        estado_p = _clasificar_vs_rango(plaq, rmin, rmax)
        detalle["plaq"] = str(plaq)
        detalle["plaq_estado"] = estado_p
        fp = _frase_plaquetas(plaq, estado_p)
        if fp:
            extras.append(fp)

    if rdw_t:
        rdw, res_r = rdw_t
        rmin, rmax = _ref_bounds("RDW", res_r)
        estado_r = _clasificar_vs_rango(rdw, rmin, rmax)
        detalle["rdw"] = str(rdw)
        detalle["rdw_estado"] = estado_r
        fr = _frase_rdw(rdw, estado_r)
        if fr:
            extras.append(fr)
            detalle["rdw_grado"] = _grado_anisocitosis(rdw) if estado_r == "alto" else ""

    if leu_t:
        leu, res_l = leu_t
        rmin, rmax = _ref_bounds("LEUCO", res_l)
        estado_l = _clasificar_vs_rango(leu, rmin, rmax)
        detalle["leu"] = str(leu)
        detalle["leu_estado"] = estado_l
        fl = _frase_leucocitos(leu, estado_l)
        if fl:
            extras.append(fl)
            if estado_l == "alto":
                detalle["leu_grado"] = _grado_leucocitosis(leu)
            elif estado_l == "bajo":
                detalle["leu_grado"] = _grado_leucopenia(leu)

    if not partes_principales and not extras:
        if not vals:
            texto = ""
            vacio = True
        else:
            texto = "Hemograma sin desviaciones relevantes respecto a los valores de referencia."
            vacio = False
    else:
        vacio = False
        if partes_principales:
            texto = partes_principales[0]
            if extras:
                texto = f"{texto}, con {', '.join(extras)}."
            else:
                texto = f"{texto}."
        else:
            # Solo extras (p. ej. trombocitopenia aislada)
            if len(extras) == 1:
                texto = extras[0][0].upper() + extras[0][1:] + "."
            else:
                texto = extras[0][0].upper() + extras[0][1:]
                texto = f"{texto}, con {', '.join(extras[1:])}."

    return {
        "texto": texto.strip(),
        "fuente": "reglas",
        "marcado_sugerencia": True,
        "detalle": detalle,
        "vacio": vacio,
    }


def sugerir_conclusion_hemograma(
    solicitud,
    *,
    prefer_medgemma: bool = True,
    valores_borrador: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Orquesta MedGemma (si está habilitado) con fallback a reglas.
    No persiste; el operador debe guardar observaciones explícitamente.
    ``valores_borrador`` permite sugerir con lo tipeado en pantalla sin guardar aún.
    """
    from laboratorio.medgemma_client import intentar_conclusion_medgemma

    reglas = construir_conclusion_hemograma_reglas(solicitud, valores_borrador=valores_borrador)
    if not prefer_medgemma:
        return reglas

    med = intentar_conclusion_medgemma(
        solicitud,
        borrador_reglas=reglas.get("texto") or "",
        valores_borrador=valores_borrador,
    )
    if med and med.get("texto"):
        return med
    return reglas
