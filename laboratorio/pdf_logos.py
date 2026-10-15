"""
Logos institucionales ICPL + CEHTA para PDFs de laboratorio (pedido e informe).

Coordenadas absolutas ReportLab: ``y_bottom`` = borde inferior de la caja del logo.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from laboratorio.informe_pdf_config import INFORME_LAB_CONFIG, LABORATORIO_STATIC

CEHTA_LOGO = "cehta_logo.png"


def draw_logo_icpl(
    c,
    x: float,
    y_bottom: float,
    w: float,
    h: float,
    *,
    anchor: str = "w",
) -> None:
    path = LABORATORIO_STATIC / (INFORME_LAB_CONFIG.get("logo") or "icpl_logo.png")
    if path.is_file():
        try:
            c.drawImage(
                ImageReader(str(path)),
                x,
                y_bottom,
                width=w,
                height=h,
                preserveAspectRatio=True,
                anchor=anchor,
                mask="auto",
            )
            return
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 10)
    if anchor == "c":
        c.drawCentredString(x + w / 2, y_bottom + h / 2, "PUEBLO DE LUIS")
    else:
        c.drawString(x, y_bottom + h / 2, "PUEBLO DE LUIS")


def draw_logo_cehta(c, right_x: float, y_bottom: float, w: float, h: float) -> None:
    """Dibuja CEHTA alineado a ``right_x`` (borde derecho de la caja)."""
    fname = INFORME_LAB_CONFIG.get("logo_cehta") or CEHTA_LOGO
    path = LABORATORIO_STATIC / fname
    if path.is_file():
        try:
            c.drawImage(
                ImageReader(str(path)),
                right_x - w,
                y_bottom,
                width=w,
                height=h,
                preserveAspectRatio=True,
                anchor="e",
                mask="auto",
            )
            return
        except Exception:
            pass
    # Fallback vectorial (mismo arte que el pedido papel).
    rojo = colors.HexColor("#B3122E")
    azul = colors.HexColor("#1F3A6E")
    x0 = right_x - w
    base = y_bottom + h
    c.saveState()
    c.setFillColor(rojo)
    c.setFont("Times-Bold", 17)
    c.drawString(x0, base - 6.2 * mm, "CEHTA")
    ancho_cehta = c.stringWidth("CEHTA", "Times-Bold", 17)
    c.setFont("Helvetica-Bold", 7.2)
    c.drawString(x0, base - 9.4 * mm, "CARDIOVASCULAR")
    c.setFillColor(azul)
    c.setFont("Helvetica", 4.2)
    c.drawString(x0, base - 11.6 * mm, "CENTRO DE HIPERTENSIÓN ARTERIAL")
    c.drawString(x0, base - 13.3 * mm, "Y ENFERMEDADES CARDIOVASCULARES")
    hx = x0 + ancho_cehta + 2.5 * mm
    hy = base - 5.5 * mm
    c.setStrokeColor(rojo)
    c.setLineWidth(1.1)
    p = c.beginPath()
    p.moveTo(hx + 4 * mm, hy - 5 * mm)
    p.curveTo(hx - 1 * mm, hy - 1.5 * mm, hx + 0.5 * mm, hy + 3.2 * mm, hx + 4 * mm, hy + 1 * mm)
    p.curveTo(hx + 7.5 * mm, hy + 3.2 * mm, hx + 9 * mm, hy - 1.5 * mm, hx + 4 * mm, hy - 5 * mm)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColor(azul)
    c.setLineWidth(0.7)
    c.line(hx - 1 * mm, hy - 1.2 * mm, hx + 2 * mm, hy - 1.2 * mm)
    c.line(hx + 2 * mm, hy - 1.2 * mm, hx + 3 * mm, hy + 1.5 * mm)
    c.line(hx + 3 * mm, hy + 1.5 * mm, hx + 4.2 * mm, hy - 3 * mm)
    c.line(hx + 4.2 * mm, hy - 3 * mm, hx + 5 * mm, hy - 1.2 * mm)
    c.line(hx + 5 * mm, hy - 1.2 * mm, hx + 10.5 * mm, hy - 1.2 * mm)
    c.restoreState()
