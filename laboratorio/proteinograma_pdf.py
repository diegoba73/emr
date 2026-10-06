"""
Bloque PDF del proteinograma electroforético (tabla % / g/dL / ref).
"""
from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from laboratorio.informe_pdf_config import INFORME_TYPO
from laboratorio.models import ResultadoExamen
from laboratorio.proteinograma import (
    CODIGO_ELP_AG,
    CODIGO_ELP_CONC,
    CODIGO_PROT_T,
    CODIGOS_ELP_FRACCIONES,
    ETIQUETAS_ELP,
    _as_decimal,
    formatear_gdl,
    formatear_pct,
    porcentajes_proteinograma,
)

COL_TOTAL = 17.2 * cm
COL_LABEL = 5.4 * cm
COL_PCT = 2.2 * cm
COL_GDL = 2.6 * cm
COL_REF_ELP = COL_TOTAL - COL_LABEL - COL_PCT - COL_GDL


def _escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _referencia_texto(res: ResultadoExamen | None) -> str:
    if res is None:
        return ""
    snap = (getattr(res, "rango_referencia_snapshot", None) or "").strip()
    if snap:
        return snap
    te = res.tipo_examen
    txt = (getattr(te, "rango_referencia_texto", None) or "").strip()
    if txt:
        return txt
    rmin = getattr(res, "rango_min_snapshot", None)
    rmax = getattr(res, "rango_max_snapshot", None)
    if rmin is None:
        rmin = getattr(te, "rango_min", None)
    if rmax is None:
        rmax = getattr(te, "rango_max", None)
    if rmin is not None and rmax is not None:
        return f"{rmin} - {rmax}"
    return ""


def _metodo_texto(res: ResultadoExamen | None) -> str:
    if res is None:
        return ""
    te = res.tipo_examen
    return (getattr(te, "metodo", None) or "").strip()


def _valor_texto(res: ResultadoExamen | None, fallback_num: Any = None) -> str:
    if res is not None:
        raw = (res.valor_obtenido or "").strip()
        if raw:
            return raw.replace(".", ",")
        if res.valor_numerico is not None:
            return formatear_gdl(res.valor_numerico)
    return formatear_gdl(fallback_num)


def _resultados_por_codigo(resultados: list[ResultadoExamen]) -> dict[str, ResultadoExamen]:
    out: dict[str, ResultadoExamen] = {}
    for res in resultados:
        codigo = (getattr(res.tipo_examen, "codigo", None) or "").strip().upper()
        if codigo:
            out[codigo] = res
    return out


def _celda(
    text: str,
    style: ParagraphStyle,
    *,
    align: int | None = None,
) -> Paragraph:
    if align is None:
        return Paragraph(_escape(text or "—"), style)
    aligned = ParagraphStyle(
        f"{style.name}_align_{align}",
        parent=style,
        alignment=align,
    )
    return Paragraph(_escape(text or "—"), aligned)


def bloque_proteinograma(
    grupo: Any,
    styles: dict[str, ParagraphStyle],
    *,
    valores_por_codigo: dict[str, Any] | None = None,
) -> list[Any]:
    """
    Layout clínico: título, material/método, tabla %/g/dL/ref,
    relación A/G y observaciones (ELP_CONC).
    """
    flow: list[Any] = []
    resultados: list[ResultadoExamen] = list(getattr(grupo, "resultados", []) or [])
    by_code = _resultados_por_codigo(resultados)
    vals = dict(valores_por_codigo or {})
    for codigo, res in by_code.items():
        if codigo not in vals or vals[codigo] is None:
            num = res.valor_numerico
            if num is None and (res.valor_obtenido or "").strip():
                num = _as_decimal(res.valor_obtenido)
            vals[codigo] = num

    pct_map = porcentajes_proteinograma(vals)
    titulo = (getattr(grupo, "titulo", None) or "Proteinograma electroforético").upper()

    panel_header = Table(
        [[Paragraph(_escape(titulo), styles["panel"])]],
        colWidths=[COL_TOTAL],
    )
    panel_header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(INFORME_TYPO["color_panel_bg"])),
                ("LINEBELOW", (0, 0), (-1, -1), 0.8, colors.HexColor(INFORME_TYPO["color_rule"])),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    flow.append(panel_header)

    metodo = ""
    for codigo in (CODIGO_PROT_T, *CODIGOS_ELP_FRACCIONES):
        metodo = _metodo_texto(by_code.get(codigo)) or metodo
    flow.append(Paragraph("Material: suero", styles["panel_meta"]))
    if metodo:
        flow.append(Paragraph(f"Método: {_escape(metodo)}", styles["panel_meta"]))
    flow.append(Spacer(1, 0.12 * cm))

    flow.append(Paragraph("FRACCIONAMIENTO PROTEICO", styles["observaciones_title"]))
    header = [
        _celda("", styles["table_header"], align=TA_LEFT),
        _celda("%", styles["table_header"], align=TA_RIGHT),
        _celda("g/dL", styles["table_header"], align=TA_RIGHT),
        _celda("Intervalo de referencia", styles["table_header"], align=TA_LEFT),
    ]
    data: list[list[Any]] = [header]

    res_pt = by_code.get(CODIGO_PROT_T)
    gdl_pt = _valor_texto(res_pt, vals.get(CODIGO_PROT_T))
    ref_pt = _referencia_texto(res_pt) or "6.3 - 7.9 g/dL"
    data.append(
        [
            _celda(ETIQUETAS_ELP[CODIGO_PROT_T], styles["exam_title"], align=TA_LEFT),
            _celda("", styles["result_value"], align=TA_RIGHT),
            _celda(gdl_pt or "—", styles["result_value"], align=TA_RIGHT),
            _celda(ref_pt or "—", styles["result_ref"], align=TA_LEFT),
        ]
    )

    for codigo in CODIGOS_ELP_FRACCIONES:
        res = by_code.get(codigo)
        gdl = _valor_texto(res, vals.get(codigo))
        pct = formatear_pct(pct_map.get(codigo))
        ref = _referencia_texto(res) or "—"
        data.append(
            [
                _celda(ETIQUETAS_ELP.get(codigo, codigo), styles["exam_title"], align=TA_LEFT),
                _celda(pct or "—", styles["result_value"], align=TA_RIGHT),
                _celda(gdl or "—", styles["result_value"], align=TA_RIGHT),
                _celda(ref, styles["result_ref"], align=TA_LEFT),
            ]
        )

    res_ag = by_code.get(CODIGO_ELP_AG)
    ag_txt = _valor_texto(res_ag, vals.get(CODIGO_ELP_AG))
    data.append(
        [
            _celda(ETIQUETAS_ELP[CODIGO_ELP_AG], styles["exam_title"], align=TA_LEFT),
            _celda(ag_txt or "—", styles["result_value"], align=TA_RIGHT),
            _celda("", styles["result_value"], align=TA_RIGHT),
            _celda("", styles["result_ref"], align=TA_LEFT),
        ]
    )

    tbl = Table(data, colWidths=[COL_LABEL, COL_PCT, COL_GDL, COL_REF_ELP])
    tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(INFORME_TYPO["color_rule"])),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (1, 0), (2, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (0, -1), 2),
                ("LEFTPADDING", (1, 0), (2, -1), 2),
                ("RIGHTPADDING", (1, 0), (2, -1), 6),
            ]
        )
    )
    flow.append(tbl)
    flow.append(Spacer(1, 0.18 * cm))

    res_conc = by_code.get(CODIGO_ELP_CONC)
    conc = (res_conc.valor_obtenido or "").strip() if res_conc is not None else ""
    if conc:
        flow.append(Paragraph("Observaciones:", styles["observaciones_title"]))
        flow.append(
            Paragraph(_escape(conc).replace("\n", "<br/>"), styles["observaciones"])
        )

    flow.append(Spacer(1, 0.25 * cm))
    return [KeepTogether(flow)]
