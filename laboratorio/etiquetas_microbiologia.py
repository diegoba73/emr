"""
Etiquetas PDF Code128 para estudios de microbiología (independientes de tubos LIMS).
"""
from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from laboratorio.etiquetas_muestra import (
    COLS,
    GAP_X,
    GAP_Y,
    LABEL_H,
    LABEL_W,
    MARGIN_X,
    MARGIN_Y,
    ROWS,
    _barcode_reader,
    _format_fecha,
    _truncate,
)
from laboratorio.models_microbiologia import EstudioMicrobiologia


def _draw_label_micro(c: canvas.Canvas, x: float, y: float, estudio: EstudioMicrobiologia) -> None:
    pac = estudio.paciente
    codigo = estudio.codigo_barra or f"MIC#{estudio.pk}"
    cultivo = estudio.tipo_cultivo.nombre if estudio.tipo_cultivo_id else estudio.tipo_estudio
    muestra = estudio.tipo_muestra_micro.nombre if estudio.tipo_muestra_micro_id else "—"

    c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)

    img = _barcode_reader(codigo)
    bc_h = 6.5 * mm
    bc_w = LABEL_W - 3 * mm
    c.drawImage(
        img,
        x + 1.5 * mm,
        y + LABEL_H - bc_h - 1.2 * mm,
        width=bc_w,
        height=bc_h,
        preserveAspectRatio=True,
        anchor="sw",
    )

    ty = y + LABEL_H - bc_h - 3 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x + 1.5 * mm, ty, codigo)

    line = 2.2 * mm
    c.setFont("Helvetica-Bold", 5.5)
    ty -= line
    c.drawString(x + 1.5 * mm, ty, _truncate(cultivo, 42))

    c.setFont("Helvetica", 5)
    ty -= line
    c.drawString(x + 1.5 * mm, ty, _truncate(f"Muestra: {muestra}", 42))
    ty -= line
    c.drawString(x + 1.5 * mm, ty, _truncate(f"Est: {estudio.numero or estudio.pk}", 42))
    ty -= line
    dni = getattr(pac, "dni", None) or "—"
    nombre = getattr(pac, "nombre_completo", None) or (
        f"{getattr(pac, 'apellido', '')}, {getattr(pac, 'nombre', '')}".strip(", ")
    )
    c.drawString(x + 1.5 * mm, ty, _truncate(f"{nombre}  DNI {dni}", 44))
    ty -= line
    fecha_txt = _format_fecha(estudio.etiquetas_impresas_at or estudio.created_at)
    if fecha_txt:
        c.drawString(x + 1.5 * mm, ty, fecha_txt)


def generar_etiquetas_micro_pdf_bytes(estudios: list[EstudioMicrobiologia]) -> bytes:
    if not estudios:
        raise ValueError("Sin estudios para etiquetas.")
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    idx = 0
    for estudio in estudios:
        col = idx % COLS
        row = (idx // COLS) % ROWS
        if idx > 0 and col == 0 and row == 0:
            c.showPage()
        x = MARGIN_X + col * (LABEL_W + GAP_X)
        y = page_h - MARGIN_Y - (row + 1) * LABEL_H - row * GAP_Y
        _draw_label_micro(c, x, y, estudio)
        idx += 1
    c.save()
    buf.seek(0)
    return buf.read()


def nombre_archivo_etiquetas_micro(estudio_ids: list[int]) -> str:
    if len(estudio_ids) == 1:
        return f"etiquetas-micro-{estudio_ids[0]}.pdf"
    return f"etiquetas-micro-{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
