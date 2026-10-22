"""
Bloque PDF de la prueba oral de tolerancia a la glucosa (CTOG).

Formato clínico: título, muestra/método/sobrecarga y tabla Tiempo | Resultado | Ref.
Solo basal (0 min) y 120 minutos.
"""
from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from laboratorio.ctog import (
    CODIGOS_CTOG,
    ETIQUETAS_CTOG,
    METODO_INFORME_CTOG,
    MUESTRA_INFORME_CTOG,
    REF_CTOG,
    SOBRECARGA_INFORME_CTOG,
    TITULO_INFORME_CTOG,
)
from laboratorio.informe_pdf_config import INFORME_TYPO
from laboratorio.models import ResultadoExamen

COL_TOTAL = 17.2 * cm
COL_TIEMPO = 5.2 * cm
COL_RESULTADO = 4.2 * cm
COL_REF = COL_TOTAL - COL_TIEMPO - COL_RESULTADO


def _escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _resultados_por_codigo(resultados: list[ResultadoExamen]) -> dict[str, ResultadoExamen]:
    out: dict[str, ResultadoExamen] = {}
    for res in resultados:
        codigo = (getattr(res.tipo_examen, "codigo", None) or "").strip().upper()
        if codigo:
            out[codigo] = res
    return out


def _valor_texto(res: ResultadoExamen | None) -> str:
    if res is None:
        return "—"
    raw = (res.valor_obtenido or "").strip()
    if raw:
        base = raw.replace(".", ",")
    elif res.valor_numerico is not None:
        base = str(res.valor_numerico).replace(".", ",")
    else:
        return "—"
    unidad = (res.unidad or getattr(res.tipo_examen, "unidad_default", None) or "").strip()
    if not unidad:
        unidad = "mg/dL"
    if unidad.lower() in base.lower():
        return base
    return f"{base} {unidad}"


def _referencia_texto(res: ResultadoExamen | None, codigo: str) -> str:
    if res is not None:
        snap = (getattr(res, "rango_referencia_snapshot", None) or "").strip()
        if snap:
            return snap
        te = res.tipo_examen
        txt = (getattr(te, "rango_referencia_texto", None) or "").strip()
        if txt:
            return txt
    return REF_CTOG.get(codigo, "—")


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


def bloque_ctog(
    grupo: Any,
    styles: dict[str, ParagraphStyle],
    *,
    fechas_extraccion_por_resultado: dict[int, str] | None = None,
) -> list[Any]:
    """Layout CTOG: título, meta clínica y tabla basal / 120 min."""
    flow: list[Any] = []
    resultados: list[ResultadoExamen] = list(getattr(grupo, "resultados", []) or [])
    by_code = _resultados_por_codigo(resultados)

    panel_header = Table(
        [[Paragraph(_escape(TITULO_INFORME_CTOG), styles["panel"])]],
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
    flow.append(Paragraph(f"Muestra: {_escape(MUESTRA_INFORME_CTOG)}", styles["panel_meta"]))
    flow.append(Paragraph(f"Método: {_escape(METODO_INFORME_CTOG)}", styles["panel_meta"]))
    flow.append(
        Paragraph(f"Sobrecarga oral: {_escape(SOBRECARGA_INFORME_CTOG)}", styles["panel_meta"])
    )

    fechas_ext = fechas_extraccion_por_resultado or {}
    ext_panel = ""
    for res in resultados:
        cand = (fechas_ext.get(res.pk) or "").strip()
        if cand and cand != "—":
            ext_panel = cand
            break
    if ext_panel:
        flow.append(Paragraph(f"Extracción: {_escape(ext_panel)}", styles["panel_meta"]))
    flow.append(Spacer(1, 0.14 * cm))

    header = [
        _celda("Tiempo", styles["table_header"], align=TA_LEFT),
        _celda("Resultado", styles["table_header"], align=TA_RIGHT),
        _celda("Valor de referencia", styles["table_header"], align=TA_LEFT),
    ]
    data: list[list[Any]] = [header]
    for codigo in CODIGOS_CTOG:
        res = by_code.get(codigo)
        data.append(
            [
                _celda(ETIQUETAS_CTOG.get(codigo, codigo), styles["exam_title"], align=TA_LEFT),
                _celda(_valor_texto(res), styles["result_value"], align=TA_RIGHT),
                _celda(_referencia_texto(res, codigo), styles["result_ref"], align=TA_LEFT),
            ]
        )

    tbl = Table(data, colWidths=[COL_TIEMPO, COL_RESULTADO, COL_REF])
    tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(INFORME_TYPO["color_rule"])),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 2),
                ("RIGHTPADDING", (1, 0), (1, -1), 6),
            ]
        )
    )
    flow.append(tbl)
    flow.append(Spacer(1, 0.25 * cm))
    return [KeepTogether(flow)]
