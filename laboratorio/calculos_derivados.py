"""
Parametros clinicos derivados (informe / carga LIMS).

Perfil lipidico — se cargan COL_TOT, HDL, TG; el resto se calcula.
Hepatograma — BIL_I = BIL_T - BIL_D.
Hemograma — VCM, HCM, CHCM (y absolutos de formula leucocitaria).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from laboratorio.entrada_resultados import quantize_valor_numerico

TG_MAX_FRIEDEWALD = Decimal("400")
RESULTADO_NO_CALCULABLE = "No calculable con estos datos"
CODIGOS_LIPIDO_MEDIDOS = frozenset({"COL_TOT", "HDL", "TG"})
CODIGOS_LIPIDO_CALCULADOS = frozenset(
    {"LDL", "VLDL", "COL_NO_LDL", "COL_RESID", "RATIO_CT_HDL"}
)
CODIGOS_HEPAT_CALCULADOS = frozenset({"BIL_I"})
CODIGOS_HEMO_INDICES = frozenset({"VCM", "HCM", "CHCM"})
CODIGOS_CALCULADOS = CODIGOS_LIPIDO_CALCULADOS | CODIGOS_HEPAT_CALCULADOS
FORMULA_LEUCO_CODIGOS = frozenset(
    {"NEUT_CAY", "NEUT_SEG", "EOS", "BAS", "LINF", "MONO"}
)


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _q(value: Decimal, places: int) -> Decimal:
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def _fmt(value: Decimal, places: int) -> str:
    q = _q(value, places)
    if places == 0:
        return str(int(q))
    text = f"{q:.{places}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def calc_vldl(tg: Decimal) -> Decimal:
    return _q(tg / Decimal(5), 0)


def calc_ldl_friedewald(col_tot: Decimal, hdl: Decimal, tg: Decimal) -> Decimal | None:
    if tg >= TG_MAX_FRIEDEWALD:
        return None
    return _q(col_tot - hdl - (tg / Decimal(5)), 0)


def calc_col_no_hdl(col_tot: Decimal, hdl: Decimal) -> Decimal:
    return _q(col_tot - hdl, 0)


def calc_col_residual(col_tot: Decimal, hdl: Decimal, ldl: Decimal) -> Decimal:
    return _q(col_tot - hdl - ldl, 0)


def calc_ratio_ct_hdl(col_tot: Decimal, hdl: Decimal) -> Decimal | None:
    if hdl <= 0:
        return None
    return _q(col_tot / hdl, 2)


def calc_bil_indirecta(bil_t: Decimal, bil_d: Decimal) -> Decimal | None:
    if bil_t < bil_d:
        return None
    return _q(bil_t - bil_d, 2)


def calc_vcm(hto: Decimal, hematies: Decimal) -> Decimal | None:
    if hematies <= 0:
        return None
    return _q((hto / hematies) * Decimal(10), 2)


def calc_hcm(hgb: Decimal, hematies: Decimal) -> Decimal | None:
    if hematies <= 0:
        return None
    return _q((hgb / hematies) * Decimal(10), 2)


def calc_chcm(hgb: Decimal, hto: Decimal) -> Decimal | None:
    if hto <= 0:
        return None
    return _q((hgb / hto) * Decimal(100), 2)


def calc_absoluto_formula(pct: Decimal, leucos: Decimal) -> int | None:
    if leucos < 0 or pct < 0:
        return None
    return int(_q(pct * leucos / Decimal(100), 0))


def format_absoluto_mm3(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def calcular_derivados(valores: dict[str, Decimal | None]) -> dict[str, tuple[Decimal | None, str]]:
    out: dict[str, tuple[Decimal | None, str]] = {}

    col = _dec(valores.get("COL_TOT"))
    hdl = _dec(valores.get("HDL"))
    tg = _dec(valores.get("TG"))
    if col is not None and hdl is not None:
        no_hdl = calc_col_no_hdl(col, hdl)
        out["COL_NO_LDL"] = (quantize_valor_numerico(no_hdl), _fmt(no_hdl, 0))
        ratio = calc_ratio_ct_hdl(col, hdl)
        if ratio is not None:
            out["RATIO_CT_HDL"] = (quantize_valor_numerico(ratio), _fmt(ratio, 2))
        if tg is not None:
            vldl = calc_vldl(tg)
            out["VLDL"] = (quantize_valor_numerico(vldl), _fmt(vldl, 0))
            ldl = calc_ldl_friedewald(col, hdl, tg)
            if ldl is not None:
                out["LDL"] = (quantize_valor_numerico(ldl), _fmt(ldl, 0))
                resid = calc_col_residual(col, hdl, ldl)
                out["COL_RESID"] = (quantize_valor_numerico(resid), _fmt(resid, 0))
            else:
                # TG ≥ 400: Friedewald no aplicable — no dejar valor anterior.
                out["LDL"] = (None, RESULTADO_NO_CALCULABLE)
                out["COL_RESID"] = (None, RESULTADO_NO_CALCULABLE)
        else:
            # Falta TG: no inventar VLDL/LDL/residual.
            out["VLDL"] = (None, RESULTADO_NO_CALCULABLE)
            out["LDL"] = (None, RESULTADO_NO_CALCULABLE)
            out["COL_RESID"] = (None, RESULTADO_NO_CALCULABLE)

    bil_t = _dec(valores.get("BIL_T"))
    bil_d = _dec(valores.get("BIL_D"))
    if bil_t is not None and bil_d is not None:
        bil_i = calc_bil_indirecta(bil_t, bil_d)
        if bil_i is not None:
            out["BIL_I"] = (quantize_valor_numerico(bil_i), _fmt(bil_i, 2))
        else:
            out["BIL_I"] = (None, RESULTADO_NO_CALCULABLE)

    hgb = _dec(valores.get("HGB"))
    hto = _dec(valores.get("HTO"))
    rbc = _dec(valores.get("HEMATIES"))
    if hto is not None and rbc is not None:
        vcm = calc_vcm(hto, rbc)
        if vcm is not None:
            out["VCM"] = (quantize_valor_numerico(vcm), _fmt(vcm, 2))
    if hgb is not None and rbc is not None:
        hcm = calc_hcm(hgb, rbc)
        if hcm is not None:
            out["HCM"] = (quantize_valor_numerico(hcm), _fmt(hcm, 2))
    if hgb is not None and hto is not None:
        chcm = calc_chcm(hgb, hto)
        if chcm is not None:
            out["CHCM"] = (quantize_valor_numerico(chcm), _fmt(chcm, 2))

    return out


def es_codigo_calculado(codigo: str | None) -> bool:
    return (codigo or "").strip().upper() in CODIGOS_CALCULADOS


def aplicar_calculos_derivados_solicitud(
    solicitud, *, solo_calculados: bool = True, actor=None, view: str = "calculos_derivados"
) -> int:
    from auditoria.audit_service import log_update
    from auditoria.snapshot import safe_model_snapshot
    from laboratorio.models import ResultadoExamen
    from laboratorio.resultados_clinicos import aplicar_carga_estructurada

    rows = list(
        ResultadoExamen.objects.select_related("tipo_examen").filter(solicitud=solicitud)
    )
    if not rows:
        return 0

    by_codigo: dict[str, Any] = {}
    valores: dict[str, Decimal | None] = {}
    for res in rows:
        codigo = (getattr(res.tipo_examen, "codigo", None) or "").strip().upper()
        if not codigo:
            continue
        by_codigo[codigo] = res
        num = _dec(res.valor_numerico)
        if num is None:
            num = _dec(res.valor_obtenido)
        valores[codigo] = num

    derivados = calcular_derivados(valores)
    if solo_calculados:
        derivados = {k: v for k, v in derivados.items() if k in CODIGOS_CALCULADOS}

    actualizados = 0
    for codigo, (num, texto) in derivados.items():
        res = by_codigo.get(codigo)
        if res is None:
            continue
        if res.validado_por_id or res.fecha_validacion:
            continue
        before = safe_model_snapshot(res)
        item = {"valor": texto, "valor_obtenido": texto, "valor_numerico": num}
        aplicar_carga_estructurada(res, res.tipo_examen, item)
        res.save()
        log_update(
            actor=actor, entity=res, before=before, module="laboratorio",
            metadata={"accion": "recalcular_resultado", "view": view,
                      "solicitud_id": solicitud.pk, "tipo_examen_id": res.tipo_examen_id,
                      "calculable": num is not None},
        )
        actualizados += 1
    return actualizados
