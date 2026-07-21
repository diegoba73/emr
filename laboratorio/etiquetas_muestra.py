"""
Generación de etiquetas PDF con código de barras Code128 para muestras LIMS.
Tamaño pensado para wrap en tubos 12×56 mm (~45×20 mm).
"""
from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from laboratorio.models_catalog import Muestra

# Wrap-around para tubos 12×56 mm
LABEL_W = 45 * mm
LABEL_H = 20 * mm
COLS = 4
ROWS = 13
MARGIN_X = 6 * mm
MARGIN_Y = 8 * mm
GAP_X = 2 * mm
GAP_Y = 1 * mm


def _barcode_reader(codigo: str) -> ImageReader:
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError as exc:
        raise RuntimeError(
            "Falta la dependencia python-barcode. Instalá con: pip install python-barcode Pillow"
        ) from exc
    writer = ImageWriter()
    writer.set_options(
        {
            "module_width": 0.22,
            "module_height": 5.5,
            "quiet_zone": 1.0,
            "write_text": False,
        }
    )
    code128 = barcode.get_barcode_class("code128")
    bc = code128(codigo, writer=writer)
    buf = BytesIO()
    bc.write(buf)
    buf.seek(0)
    return ImageReader(buf)


def _truncate(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _format_fecha(dt) -> str:
    if not dt:
        return ""
    local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    return local.strftime("%d/%m/%Y %H:%M")


def _draw_label(c: canvas.Canvas, x: float, y: float, muestra: Muestra) -> None:
    sol = muestra.solicitud
    pac = muestra.paciente
    tm = muestra.tipo_muestra
    tc = muestra.tipo_contenedor
    codigo = muestra.codigo_barra or f"M#{muestra.pk}"

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

    c.setFont("Helvetica-Bold", 5.5)
    line = 2.2 * mm
    ty -= line
    if tc:
        tubo_txt = f"{tc.codigo} — {tc.nombre}"
    else:
        tubo_txt = f"{tm.codigo} — {tm.nombre}"
    c.drawString(x + 1.5 * mm, ty, _truncate(tubo_txt, 42))

    c.setFont("Helvetica", 5)
    ty -= line
    c.drawString(x + 1.5 * mm, ty, _truncate(f"Ord: {sol.numero or sol.pk}", 42))
    ty -= line
    dni = getattr(pac, "dni", None) or "—"
    c.drawString(x + 1.5 * mm, ty, _truncate(f"{pac.nombre_completo}  DNI {dni}", 44))
    ty -= line
    fecha_txt = _format_fecha(muestra.fecha_toma or muestra.created_at)
    if fecha_txt:
        c.drawString(x + 1.5 * mm, ty, fecha_txt)


def generar_etiqueta_muestra_pdf_bytes(muestra: Muestra) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(LABEL_W + 4 * mm, LABEL_H + 4 * mm))
    _draw_label(c, 2 * mm, 2 * mm, muestra)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def generar_etiquetas_muestras_pdf_bytes(muestras: list[Muestra]) -> bytes:
    if not muestras:
        raise ValueError("Sin muestras para etiquetas.")
    buf = BytesIO()
    page_w, page_h = A4
    c = canvas.Canvas(buf, pagesize=A4)
    col = 0
    row = 0
    for i, m in enumerate(muestras):
        x = MARGIN_X + col * (LABEL_W + GAP_X)
        y = page_h - MARGIN_Y - LABEL_H - row * (LABEL_H + GAP_Y)
        _draw_label(c, x, y, m)
        col += 1
        if col >= COLS:
            col = 0
            row += 1
            if row >= ROWS and i < len(muestras) - 1:
                c.showPage()
                row = 0
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def nombre_archivo_etiqueta_muestra(muestra_id: int, codigo: str | None) -> str:
    safe = (codigo or str(muestra_id)).replace("/", "-")
    return f"etiqueta-muestra-{safe}.pdf"


def nombre_archivo_etiquetas_orden(solicitud_id: int, numero: str | None) -> str:
    ref = (numero or str(solicitud_id)).replace("/", "-")
    return f"etiquetas-orden-{ref}.pdf"
