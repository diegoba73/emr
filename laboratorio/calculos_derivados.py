"""
Parametros clinicos derivados (informe / carga LIMS).

Perfil lipidico — se cargan COL_TOT, HDL, TG; el resto se calcula.
Hepatograma — BIL_I = BIL_T - BIL_D.
Hemograma — VCM, HCM, CHCM (y absolutos de formula leucocitaria).
Perfil ferrico — se cargan FERR, UIBC (, FERRIT); CF, SAT_FE y TRANS se calculan.
Clearance — se cargan CREATI, CREA_U, DIUR; CLEAR_CREA se calcula.
Orinas 24 hs — concentración + DIUR → excreción (PROT_U_24, NA/K/CL_U24, MICROALB_24).
RAC — se cargan MICROALB + CREA_U; RAC (mg/g) = (MICROALB / CREA_U) × 100.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from laboratorio.entrada_resultados import quantize_valor_numerico

TG_MAX_FRIEDEWALD = Decimal("400")
RESULTADO_NO_CALCULABLE = "No calculable con estos datos"
MINUTOS_24H = Decimal("1440")
CODIGOS_LIPIDO_MEDIDOS = frozenset({"COL_TOT", "HDL", "TG"})
CODIGOS_LIPIDO_CALCULADOS = frozenset(
    {"LDL", "VLDL", "COL_NO_LDL", "COL_RESID", "RATIO_CT_HDL"}
)
CODIGOS_HEPAT_CALCULADOS = frozenset({"BIL_I"})
CODIGOS_HEMO_INDICES = frozenset({"VCM", "HCM", "CHCM"})
# TIBC = FERR + UIBC; saturación = FERR/TIBC×100; transferrina ≈ TIBC×0.8
CODIGOS_FERRICO_CALCULADOS = frozenset({"CF", "SAT_FE", "TRANS"})
CODIGOS_CLEARANCE_CALCULADOS = frozenset({"CLEAR_CREA"})
CODIGOS_ORINA_24H_CALCULADOS = frozenset(
    {"PROT_U_24", "NA_U24", "K_U24", "CL_U24", "MICROALB_24"}
)
CODIGOS_RAC_CALCULADOS = frozenset({"RAC"})
CODIGOS_CALCULADOS = (
    CODIGOS_LIPIDO_CALCULADOS
    | CODIGOS_HEPAT_CALCULADOS
    | CODIGOS_FERRICO_CALCULADOS
    | CODIGOS_CLEARANCE_CALCULADOS
    | CODIGOS_ORINA_24H_CALCULADOS
    | CODIGOS_RAC_CALCULADOS
)
# Pedido suelto del calculado → asegurar insumos medidos (p. ej. RAC solo).
INSUMOS_POR_CODIGO_CALCULADO: dict[str, tuple[str, ...]] = {
    "RAC": ("MICROALB", "CREA_U"),
}
FORMULA_LEUCO_CODIGOS = frozenset(
    {"NEUT_CAY", "NEUT_SEG", "EOS", "BAS", "LINF", "MONO"}
)
# Factor habitual: transferrina (mg/dL) ≈ TIBC (µg/dL) × 0.8
FACTOR_TRANS_DESDE_TIBC = Decimal("0.8")


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


def calc_tibc(ferremia: Decimal, uibc: Decimal) -> Decimal:
    """Capacidad total de fijación (µg/dL) = ferremia + UIBC."""
    return _q(ferremia + uibc, 0)


def calc_sat_transferrina(ferremia: Decimal, tibc: Decimal) -> Decimal | None:
    """% saturación = (ferremia / TIBC) × 100."""
    if tibc <= 0:
        return None
    return _q((ferremia / tibc) * Decimal(100), 1)


def calc_transferrina_desde_tibc(tibc: Decimal) -> Decimal:
    """Transferrina (mg/dL) ≈ TIBC (µg/dL) × 0.8."""
    return _q(tibc * FACTOR_TRANS_DESDE_TIBC, 0)


def calc_clearance_creatinina(
    creati: Decimal, crea_u: Decimal, diur: Decimal
) -> Decimal | None:
    """Clearance (mL/min) = (creatinuria × diuresis) / (creatininemia × 1440)."""
    if creati <= 0:
        return None
    return _q((crea_u * diur) / (creati * MINUTOS_24H), 1)


def calc_excrecion_mg_dl_a_24h(conc_mg_dl: Decimal, diur_ml: Decimal) -> Decimal | None:
    """mg/24 hs = concentración (mg/dL) × diuresis (mL) / 100."""
    if diur_ml <= 0:
        return None
    return _q((conc_mg_dl * diur_ml) / Decimal(100), 0)


def calc_excrecion_por_litro_a_24h(
    conc_por_l: Decimal, diur_ml: Decimal, *, places: int = 0
) -> Decimal | None:
    """Unidad/24 hs = concentración (por L) × diuresis (mL) / 1000."""
    if diur_ml <= 0:
        return None
    return _q((conc_por_l * diur_ml) / Decimal(1000), places)


def calc_rac(microalb_mg_l: Decimal, crea_u_mg_dl: Decimal) -> Decimal | None:
    """RAC (mg/g) = (microalbuminuria mg/L ÷ creatinuria mg/dL) × 100."""
    if crea_u_mg_dl <= 0:
        return None
    return _q((microalb_mg_l / crea_u_mg_dl) * Decimal(100), 1)


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

    ferr = _dec(valores.get("FERR"))
    uibc = _dec(valores.get("UIBC"))
    if ferr is not None and uibc is not None:
        tibc = calc_tibc(ferr, uibc)
        out["CF"] = (quantize_valor_numerico(tibc), _fmt(tibc, 0))
        sat = calc_sat_transferrina(ferr, tibc)
        if sat is not None:
            out["SAT_FE"] = (quantize_valor_numerico(sat), _fmt(sat, 1))
        else:
            out["SAT_FE"] = (None, RESULTADO_NO_CALCULABLE)
        trans = calc_transferrina_desde_tibc(tibc)
        out["TRANS"] = (quantize_valor_numerico(trans), _fmt(trans, 0))
    elif ferr is not None or uibc is not None:
        # Falta uno de los dos medidos: no inventar derivados férricos.
        out["CF"] = (None, RESULTADO_NO_CALCULABLE)
        out["SAT_FE"] = (None, RESULTADO_NO_CALCULABLE)
        out["TRANS"] = (None, RESULTADO_NO_CALCULABLE)

    creati = _dec(valores.get("CREATI"))
    crea_u = _dec(valores.get("CREA_U"))
    diur = _dec(valores.get("DIUR"))
    if creati is not None and crea_u is not None and diur is not None:
        clear = calc_clearance_creatinina(creati, crea_u, diur)
        if clear is not None:
            out["CLEAR_CREA"] = (quantize_valor_numerico(clear), _fmt(clear, 1))
        else:
            out["CLEAR_CREA"] = (None, RESULTADO_NO_CALCULABLE)
    elif creati is not None or crea_u is not None:
        # Falta alguno de los medidos de clearance (sin contar DIUR solo).
        out["CLEAR_CREA"] = (None, RESULTADO_NO_CALCULABLE)

    prot_eq = _dec(valores.get("PROT_U_EQ"))
    if prot_eq is not None and diur is not None:
        prot24 = calc_excrecion_mg_dl_a_24h(prot_eq, diur)
        if prot24 is not None:
            out["PROT_U_24"] = (quantize_valor_numerico(prot24), _fmt(prot24, 0))
        else:
            out["PROT_U_24"] = (None, RESULTADO_NO_CALCULABLE)
    elif prot_eq is not None:
        out["PROT_U_24"] = (None, RESULTADO_NO_CALCULABLE)

    for medido, calculado in (
        ("NA_U", "NA_U24"),
        ("K_U", "K_U24"),
        ("CL_U", "CL_U24"),
    ):
        conc = _dec(valores.get(medido))
        if conc is not None and diur is not None:
            exc = calc_excrecion_por_litro_a_24h(conc, diur, places=0)
            if exc is not None:
                out[calculado] = (quantize_valor_numerico(exc), _fmt(exc, 0))
            else:
                out[calculado] = (None, RESULTADO_NO_CALCULABLE)
        elif conc is not None:
            out[calculado] = (None, RESULTADO_NO_CALCULABLE)

    microalb = _dec(valores.get("MICROALB"))
    if microalb is not None and diur is not None:
        malb24 = calc_excrecion_por_litro_a_24h(microalb, diur, places=1)
        if malb24 is not None:
            out["MICROALB_24"] = (quantize_valor_numerico(malb24), _fmt(malb24, 1))
        else:
            out["MICROALB_24"] = (None, RESULTADO_NO_CALCULABLE)
    elif microalb is not None:
        out["MICROALB_24"] = (None, RESULTADO_NO_CALCULABLE)

    # RAC usa MICROALB + CREA_U (crea_u ya leído arriba para clearance).
    if microalb is not None and crea_u is not None:
        rac = calc_rac(microalb, crea_u)
        if rac is not None:
            out["RAC"] = (quantize_valor_numerico(rac), _fmt(rac, 1))
        else:
            out["RAC"] = (None, RESULTADO_NO_CALCULABLE)
    elif microalb is not None or crea_u is not None:
        # aplicar_* solo escribe si la orden tiene fila RAC.
        out["RAC"] = (None, RESULTADO_NO_CALCULABLE)

    return out


def es_codigo_calculado(codigo: str | None) -> bool:
    return (codigo or "").strip().upper() in CODIGOS_CALCULADOS


def codigos_insumos_de_calculados(codigos: Iterable[str]) -> list[str]:
    """Insumos medidos faltantes en ``codigos`` requeridos por calculados presentes."""
    presentes = {(c or "").strip().upper() for c in codigos if c}
    faltan: list[str] = []
    vistos: set[str] = set()
    for calc in presentes:
        for insumo in INSUMOS_POR_CODIGO_CALCULADO.get(calc, ()):
            code = (insumo or "").strip().upper()
            if not code or code in presentes or code in vistos:
                continue
            vistos.add(code)
            faltan.append(code)
    return faltan


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
