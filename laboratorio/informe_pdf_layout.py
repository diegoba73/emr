"""
Layout del informe PDF LIMS — formato clínico profesional (referencia ICPL / labs internacionales).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from laboratorio.informe_pdf_config import (
    INFORME_LAB_CONFIG,
    INFORME_TYPO,
    LABORATORIO_STATIC,
    MESES_ES,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.orden_grupos_informe import (
    PANEL_HEMOGRAMA,
    GrupoInformeSpec,
    aplicar_orden_grupos,
    construir_grupos_informe,
)
from laboratorio.procedencia_display import resolver_procedencia_solicitud
from laboratorio.solicitud_cierre import solicitud_resultados_completos

HEADER_HEIGHT = 4.2 * cm
# Reserva vertical del pie (firmas + leyendas + dirección/contacto).
FOOTER_HEIGHT = 5.2 * cm
CONTENT_TOP_PAD = 0.2 * cm
# Solo el trazo manuscrito (se recorta el texto embebido del PNG).
FIRMA_IMG_W = 6.0 * cm
FIRMA_IMG_H = 2.15 * cm
FIRMA_IMG_BOTTOM = 2.55 * cm
FIRMA_NOMBRE_Y = 2.25 * cm
FIRMA_MP_Y = 1.95 * cm
PIE_LINEA_Y = 1.55 * cm
PIE_DIR_Y = 1.22 * cm
PIE_CONTACTO_Y = 0.92 * cm
PIE_PAGINA_Y = 0.52 * cm

# Anchos de columna (total ≈ 17.2 cm útiles en A4 con márgenes 1.8 cm)
COL_EXAMEN = 5.6 * cm
COL_RESULTADO = 2.8 * cm
COL_UNIDAD = 2.0 * cm
COL_REFERENCIA = 5.4 * cm
COL_FLAG = 1.4 * cm
COL_TOTAL = COL_EXAMEN + COL_RESULTADO + COL_UNIDAD + COL_REFERENCIA + COL_FLAG


@dataclass
class GrupoResultadosPdf:
    key: str
    titulo: str
    resultados: list[ResultadoExamen] = field(default_factory=list)
    panel_codigo: str | None = None


def _escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _asset_path(filename: str | None) -> str | None:
    if not filename:
        return None
    path = LABORATORIO_STATIC / filename
    return str(path) if path.is_file() else None


def _firma_trazo_reader(path: str) -> ImageReader | None:
    """Carga la firma recortando leyendas/pie embebidos en el PNG.

    Los assets originales (360×200) traen nombre/M.P./laboratorio (y a veces
    restos de dirección) en la franja inferior; al dibujarlos enteros eso
    aparece como texto “fantasma” bajo las firmas. También el trazo toca el
    borde superior: se agrega padding para que no se vea cortado.
    """
    try:
        from PIL import Image
    except ImportError:
        return ImageReader(path)

    try:
        im = Image.open(path).convert("RGBA")
    except Exception:
        return ImageReader(path)

    w, h = im.size
    # Conservar ~78 % superior (trazo); descartar bloque de texto inferior.
    cut_y = max(1, int(h * 0.78))
    im = im.crop((0, 0, w, cut_y))

    # Recorte horizontal a tinta no blanca / no transparente.
    px = im.load()
    minx, miny, maxx, maxy = w, cut_y, 0, 0
    found = False
    for y in range(cut_y):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                continue
            if r > 248 and g > 248 and b > 248:
                continue
            found = True
            minx = min(minx, x)
            miny = min(miny, y)
            maxx = max(maxx, x)
            maxy = max(maxy, y)
    if found and maxx > minx and maxy > miny:
        pad = 4
        im = im.crop(
            (
                max(0, minx - pad),
                max(0, miny - pad),
                min(w, maxx + pad + 1),
                min(cut_y, maxy + pad + 1),
            )
        )

    # Padding superior transparente: el trazo no queda pegado al borde.
    pad_top = max(10, im.size[1] // 8)
    canvas_im = Image.new(
        "RGBA",
        (im.size[0], im.size[1] + pad_top),
        (255, 255, 255, 0),
    )
    canvas_im.paste(im, (0, pad_top), im)

    # Blancos opacos → transparentes para no tapar el pie.
    px = canvas_im.load()
    cw, ch = canvas_im.size
    for y in range(ch):
        for x in range(cw):
            r, g, b, a = px[x, y]
            if a > 0 and r > 248 and g > 248 and b > 248:
                px[x, y] = (255, 255, 255, 0)

    buf = BytesIO()
    canvas_im.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def formatear_fecha_larga(dt: datetime | date) -> str:
    if isinstance(dt, datetime):
        dt = timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()
    return f"{dt.day} de {MESES_ES[dt.month - 1]} de {dt.year}"


def formatear_paciente_apellido_nombre(paciente) -> str:
    ap = (getattr(paciente, "apellido", "") or "").strip().upper()
    nom = (getattr(paciente, "nombre", "") or "").strip().upper()
    if ap and nom:
        return f"{ap}, {nom}"
    return (getattr(paciente, "nombre_completo", "") or "—").upper()


def formatear_edad_paciente(paciente) -> str:
    edad = getattr(paciente, "edad", None)
    if edad is not None:
        return f"{edad} años"
    fn = getattr(paciente, "fecha_nacimiento", None)
    if fn:
        return formatear_fecha_larga(fn)
    return "—"


def _protocolo_display(numero: str | None, pk: int) -> str:
    if not numero:
        return str(pk)
    parts = str(numero).split("-")
    if len(parts) >= 3 and parts[-1].isdigit():
        return str(int(parts[-1]))
    return str(numero)


def _derivante_y_solicitante(procedencia: dict[str, Any]) -> tuple[str, str]:
    tipo = procedencia.get("procedencia_tipo")
    if tipo == "INTERNACION":
        sector = procedencia.get("procedencia_sector") or "Internación"
        return "Internación", sector
    if tipo == "RECURSO":
        ubic = procedencia.get("procedencia_ubicacion") or ""
        if ubic:
            return "Ambulatorio", ubic
        display = procedencia.get("procedencia_display") or "Ambulatorio"
        for token in ("CEHTA", "ICPL"):
            if token in display.upper():
                return "Ambulatorio", token
        return "Ambulatorio", display[:28]
    return "—", (procedencia.get("procedencia_display") or "—")[:28]


def agrupar_resultados_por_panel(
    solicitud: SolicitudExamen,
    resultados: list[ResultadoExamen],
) -> list[GrupoResultadosPdf]:
    specs = construir_grupos_informe(solicitud, resultados)
    orden = getattr(solicitud, "orden_grupos_informe", None) or []
    ordered: list[GrupoInformeSpec] = aplicar_orden_grupos(specs, orden if orden else None)
    return [
        GrupoResultadosPdf(
            key=g.key,
            titulo=g.titulo,
            resultados=g.resultados,
            panel_codigo=g.panel_codigo,
        )
        for g in ordered
    ]


def _referencia_texto(res: ResultadoExamen) -> str | None:
    snap = (res.rango_referencia_snapshot or "").strip()
    if snap:
        return snap
    te = res.tipo_examen
    txt = (getattr(te, "rango_referencia_texto", None) or "").strip()
    if txt:
        return txt
    vmin = res.rango_min_snapshot if res.rango_min_snapshot is not None else getattr(te, "rango_min", None)
    vmax = res.rango_max_snapshot if res.rango_max_snapshot is not None else getattr(te, "rango_max", None)
    if vmin is not None and vmax is not None:
        return f"{vmin} - {vmax}"
    return None


def _metodo_texto(res: ResultadoExamen) -> str | None:
    te = res.tipo_examen
    directo = (getattr(te, "metodo", None) or "").strip()
    if directo:
        return directo
    codigo = (getattr(te, "codigo", None) or "").strip().upper()
    cfg = INFORME_LAB_CONFIG.get("metodos_por_codigo") or {}
    if codigo and codigo in cfg:
        metodo = (cfg[codigo] or "").strip()
        return metodo or None
    default = (INFORME_LAB_CONFIG.get("metodo_default") or "").strip()
    return default or None


def _material_texto(res: ResultadoExamen) -> str | None:
    if res.muestra_id and getattr(res, "muestra", None):
        tm = getattr(res.muestra, "tipo_muestra", None)
        if tm:
            return tm.nombre
    te = res.tipo_examen
    tm_req = getattr(te, "tipo_muestra_requerida", None)
    if tm_req:
        return tm_req.nombre
    return None


def _valor_y_unidad(res: ResultadoExamen) -> tuple[str, str]:
    valor = (res.valor_obtenido or "").strip() or "—"
    unidad = (res.unidad or res.tipo_examen.unidad_default or "").strip()
    return valor, unidad


def _flag_resultado(res: ResultadoExamen) -> str:
    """Marca H/L/* según rango snapshot o flags clínicos."""
    if res.es_critico:
        return "*"
    valor = res.valor_numerico
    if valor is not None:
        vmin = res.rango_min_snapshot
        vmax = res.rango_max_snapshot
        if vmin is not None and valor < vmin:
            return "L"
        if vmax is not None and valor > vmax:
            return "H"
    if res.es_patologico:
        return "H"
    return ""


def _nombre_validador(resultados: list[ResultadoExamen]) -> tuple[str | None, datetime | None]:
    for res in resultados:
        if res.validado_por_id and res.fecha_validacion:
            user = res.validado_por
            nombre = ""
            if user is not None:
                full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
                nombre = full or getattr(user, "username", "") or str(user)
            return nombre or None, res.fecha_validacion
    for res in resultados:
        if res.validado_por_id:
            user = res.validado_por
            nombre = ""
            if user is not None:
                full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
                nombre = full or getattr(user, "username", "") or str(user)
            return nombre or None, res.fecha_validacion
    return None, None


class _InformeIcplDoc(BaseDocTemplate):
    def __init__(self, buffer, ctx: dict[str, Any], **kwargs):
        self.ctx = ctx
        super().__init__(buffer, **kwargs)
        # topMargin ya reserva HEADER_HEIGHT + CONTENT_TOP_PAD (vía self.height).
        # bottomMargin es el margen de página; el pie de firmas se reserva alzando
        # el Frame con FOOTER_HEIGHT (una sola vez). No restar HEADER otra vez:
        # eso dejaba un hueco enorme entre la caja de datos y el cuerpo.
        frame = Frame(
            self.leftMargin,
            self.bottomMargin + FOOTER_HEIGHT,
            self.width,
            self.height - FOOTER_HEIGHT,
            id="content",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(
            [
                PageTemplate(
                    id="All",
                    frames=[frame],
                    # onPageEnd: encabezado/pie DESPUÉS del cuerpo. Con onPage el
                    # story tapaba firmas y dirección (efecto “borrado”).
                    onPageEnd=self._on_page,
                )
            ]
        )

    def _on_page(self, canvas, doc):
        ctx = self.ctx
        cfg = INFORME_LAB_CONFIG
        typo = INFORME_TYPO
        w, h = A4
        canvas.saveState()

        # Limpiar zonas de encabezado/pie por si el cuerpo derramó flowables.
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(colors.white)
        canvas.rect(0, h - HEADER_HEIGHT - 0.15 * cm, w, HEADER_HEIGHT + 0.15 * cm, fill=1, stroke=0)
        canvas.rect(0, 0, w, doc.bottomMargin + FOOTER_HEIGHT, fill=1, stroke=0)
        canvas.setFillColor(colors.black)
        canvas.setStrokeColor(colors.black)

        logo = _asset_path(cfg.get("logo"))
        if logo:
            try:
                canvas.drawImage(
                    ImageReader(logo),
                    doc.leftMargin,
                    h - 2.05 * cm,
                    width=2.4 * cm,
                    height=1.35 * cm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawCentredString(w / 2, h - 1.25 * cm, cfg["titulo"])

        subtitulo = cfg.get("subtitulo_informe") or "Informe de resultados"
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor(typo["color_meta"]))
        canvas.drawCentredString(w / 2, h - 1.65 * cm, subtitulo.upper())
        canvas.setFillColor(colors.black)

        box_top = h - 2.05 * cm
        box_bottom = h - HEADER_HEIGHT + 0.25 * cm
        box_h = box_top - box_bottom
        canvas.setFillColor(colors.HexColor(typo["color_panel_bg"]))
        canvas.rect(doc.leftMargin, box_bottom, w - doc.leftMargin - doc.rightMargin, box_h, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor(typo["color_rule"]))
        canvas.setLineWidth(0.5)
        canvas.rect(doc.leftMargin, box_bottom, w - doc.leftMargin - doc.rightMargin, box_h, fill=0, stroke=1)

        mid_x = w / 2 + 0.15 * cm
        y = box_top - 0.45 * cm
        label_w = 2.8 * cm

        def row(label: str, value: str, x: float, yy: float, bold_value: bool = False):
            canvas.setFont("Helvetica", typo["header_label"])
            canvas.setFillColor(colors.HexColor(typo["color_meta"]))
            canvas.drawString(x, yy, label)
            canvas.setFillColor(colors.black)
            canvas.setFont("Helvetica-Bold" if bold_value else "Helvetica", typo["header_value"])
            canvas.drawString(x + label_w, yy, value[:42])

        row("Protocolo Nº", ctx["protocolo"], doc.leftMargin + 0.25 * cm, y, bold_value=True)
        row("Paciente", ctx["paciente"], mid_x, y, bold_value=True)
        y -= 0.38 * cm
        row("Solicitante", ctx["solicitado_por"], doc.leftMargin + 0.25 * cm, y)
        row("Historia clínica", ctx["historia_clinica"], mid_x, y)
        y -= 0.38 * cm
        row("Fecha informe", ctx["fecha"], doc.leftMargin + 0.25 * cm, y)
        row("Documento", ctx["documento"], mid_x, y)
        y -= 0.38 * cm
        row("Derivante", ctx["derivante"], doc.leftMargin + 0.25 * cm, y)
        row("Edad / F. nac.", ctx["fecha_nac"], mid_x, y)

        canvas.setLineWidth(0.8)
        canvas.line(doc.leftMargin, box_bottom - 0.08 * cm, w - doc.rightMargin, box_bottom - 0.08 * cm)

        firmas = cfg.get("firmas") or []
        slot_w = (w - doc.leftMargin - doc.rightMargin) / max(len(firmas), 1)
        for i, firma in enumerate(firmas):
            cx = doc.leftMargin + slot_w * i + slot_w / 2
            img_path = _asset_path(firma.get("imagen"))
            drew_img = False
            if img_path:
                try:
                    reader = _firma_trazo_reader(img_path)
                    if reader is not None:
                        canvas.drawImage(
                            reader,
                            cx - FIRMA_IMG_W / 2,
                            FIRMA_IMG_BOTTOM,
                            width=FIRMA_IMG_W,
                            height=FIRMA_IMG_H,
                            preserveAspectRatio=True,
                            mask="auto",
                        )
                        drew_img = True
                except Exception:
                    drew_img = False
            # Nombre / M.P. siempre desde config (el PNG ya no aporta ese texto).
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.black)
            canvas.drawCentredString(cx, FIRMA_NOMBRE_Y, firma.get("nombre", ""))
            canvas.drawCentredString(cx, FIRMA_MP_Y, f"M.P. {firma.get('mp', '')}")
            if not drew_img:
                # Sin imagen: el bloque de texto ya actúa como firma.
                pass

        canvas.setStrokeColor(colors.HexColor(typo["color_rule"]))
        canvas.setLineWidth(0.4)
        canvas.line(doc.leftMargin, PIE_LINEA_Y, w - doc.rightMargin, PIE_LINEA_Y)

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(typo["color_meta"]))
        canvas.drawCentredString(w / 2, PIE_DIR_Y, cfg["direccion_linea"])
        canvas.drawCentredString(w / 2, PIE_CONTACTO_Y, cfg["contacto_linea"])
        canvas.setFillColor(colors.black)

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - doc.rightMargin, PIE_PAGINA_Y, f"Página {doc.page}")

        canvas.restoreState()


def _styles() -> dict[str, ParagraphStyle]:
    typo = INFORME_TYPO
    meta_color = colors.HexColor(typo["color_meta"])
    return {
        "panel": ParagraphStyle(
            "PanelTitle",
            fontName="Helvetica-Bold",
            fontSize=typo["panel_title"],
            leading=typo["panel_title"] + 2,
            spaceBefore=8,
            spaceAfter=2,
            textColor=colors.black,
        ),
        "panel_meta": ParagraphStyle(
            "PanelMeta",
            fontName="Helvetica",
            fontSize=typo["panel_meta"],
            leading=typo["panel_meta"] + 2,
            textColor=meta_color,
            spaceAfter=4,
        ),
        "exam_title": ParagraphStyle(
            "ExamTitle",
            fontName="Helvetica-Bold",
            fontSize=typo["exam_title"],
            leading=typo["exam_title"] + 2,
            alignment=TA_LEFT,
        ),
        "exam_meta": ParagraphStyle(
            "ExamMeta",
            fontName="Helvetica",
            fontSize=typo["exam_meta"],
            leading=typo["exam_meta"] + 1.5,
            textColor=meta_color,
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=0,
        ),
        "result_value": ParagraphStyle(
            "ResultValue",
            fontName="Helvetica-Bold",
            fontSize=typo["result_value"],
            leading=typo["result_value"] + 2,
            alignment=TA_RIGHT,
        ),
        "result_unit": ParagraphStyle(
            "ResultUnit",
            fontName="Helvetica",
            fontSize=typo["result_unit"],
            leading=typo["result_unit"] + 2,
            alignment=TA_RIGHT,
            textColor=meta_color,
        ),
        "result_ref": ParagraphStyle(
            "ResultRef",
            fontName="Helvetica",
            fontSize=typo["exam_meta"],
            leading=typo["exam_meta"] + 1.5,
            textColor=meta_color,
            alignment=TA_LEFT,
        ),
        "result_flag": ParagraphStyle(
            "ResultFlag",
            fontName="Helvetica-Bold",
            fontSize=typo["result_value"],
            leading=typo["result_value"] + 2,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#B91C1C"),
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=typo["table_header"],
            leading=typo["table_header"] + 2,
            textColor=meta_color,
        ),
        "validation_block": ParagraphStyle(
            "ValidationBlock",
            fontName="Helvetica",
            fontSize=typo["exam_meta"],
            leading=typo["exam_meta"] + 2,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "empty": ParagraphStyle(
            "Empty",
            fontName="Helvetica-Oblique",
            fontSize=typo["exam_meta"],
            textColor=meta_color,
        ),
        "partial_banner": ParagraphStyle(
            "PartialBanner",
            fontName="Helvetica-Bold",
            fontSize=typo["panel_title"],
            leading=typo["panel_title"] + 2,
            textColor=colors.HexColor("#B45309"),
            spaceAfter=6,
        ),
        "legend": ParagraphStyle(
            "FlagLegend",
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=meta_color,
            spaceBefore=6,
        ),
        "observaciones_title": ParagraphStyle(
            "ObservacionesTitle",
            fontName="Helvetica-Bold",
            fontSize=typo["panel_title"],
            leading=typo["panel_title"] + 2,
            spaceBefore=10,
            spaceAfter=2,
        ),
        "observaciones": ParagraphStyle(
            "ObservacionesInforme",
            fontName="Helvetica",
            fontSize=typo["exam_title"],
            leading=typo["exam_title"] + 2,
            spaceBefore=2,
            spaceAfter=4,
        ),
    }


def _celda_examen(res: ResultadoExamen, styles: dict[str, ParagraphStyle]) -> list[Any]:
    nombre = _escape((res.tipo_examen.nombre or "").upper())
    parts: list[Any] = [Paragraph(nombre, styles["exam_title"])]

    metodo = _metodo_texto(res)
    if metodo:
        parts.append(Paragraph(f"Método: {_escape(metodo)}", styles["exam_meta"]))

    return parts


def _tabla_encabezado_columnas(styles: dict[str, ParagraphStyle]) -> Table:
    tbl = Table(
        [
            [
                Paragraph("EXAMEN", styles["table_header"]),
                Paragraph("RESULTADO", styles["table_header"]),
                Paragraph("UNIDAD", styles["table_header"]),
                Paragraph("REFERENCIA", styles["table_header"]),
                Paragraph("", styles["table_header"]),
            ]
        ],
        colWidths=[COL_EXAMEN, COL_RESULTADO, COL_UNIDAD, COL_REFERENCIA, COL_FLAG],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(INFORME_TYPO["color_rule"])),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (1, 0), (2, 0), "RIGHT"),
                ("ALIGN", (4, 0), (4, 0), "CENTER"),
            ]
        )
    )
    return tbl


def _fila_resultado(res: ResultadoExamen, styles: dict[str, ParagraphStyle]) -> Table:
    valor, unidad = _valor_y_unidad(res)
    ref = _referencia_texto(res) or "—"
    flag = _flag_resultado(res)

    left_parts = _celda_examen(res, styles)
    left = Table(
        [[p] for p in left_parts],
        colWidths=[COL_EXAMEN - 0.15 * cm],
    )
    left.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    row = Table(
        [
            [
                left,
                Paragraph(_escape(valor), styles["result_value"]),
                Paragraph(_escape(unidad or "—"), styles["result_unit"]),
                Paragraph(_escape(ref), styles["result_ref"]),
                Paragraph(_escape(flag), styles["result_flag"]),
            ]
        ],
        colWidths=[COL_EXAMEN, COL_RESULTADO, COL_UNIDAD, COL_REFERENCIA, COL_FLAG],
    )
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (0, 0), 2),
                ("RIGHTPADDING", (1, 0), (2, 0), 2),
                ("ALIGN", (1, 0), (2, 0), "RIGHT"),
                ("ALIGN", (4, 0), (4, 0), "CENTER"),
            ]
        )
    )
    return row


def _bloque_panel(grupo: GrupoResultadosPdf, styles: dict[str, ParagraphStyle]) -> list[Any]:
    flow: list[Any] = []

    panel_header = Table(
        [[Paragraph(_escape(grupo.titulo), styles["panel"])]],
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

    materiales = []
    for res in grupo.resultados:
        mat = _material_texto(res)
        if mat and mat not in materiales:
            materiales.append(mat)
    if materiales:
        mat_txt = " · ".join(materiales)
        flow.append(Paragraph(f"Material: {_escape(mat_txt)}", styles["panel_meta"]))

    flow.append(Spacer(1, 0.08 * cm))
    flow.append(_tabla_encabezado_columnas(styles))

    for res in grupo.resultados:
        flow.append(_fila_resultado(res, styles))

    flow.append(Spacer(1, 0.25 * cm))
    return [KeepTogether(flow)]


def _bloque_validacion(
    solicitud: SolicitudExamen,
    resultados: list[ResultadoExamen],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    flow: list[Any] = []
    nombre, fecha = _nombre_validador(resultados)
    if solicitud.estado == "FINALIZADO" and (nombre or fecha):
        fecha_txt = ""
        if fecha:
            fecha_txt = timezone.localtime(fecha).strftime("%d/%m/%Y %H:%M") if timezone.is_aware(fecha) else fecha.strftime("%d/%m/%Y %H:%M")
        partes = ["Resultados validados para emisión."]
        if nombre:
            partes.append(f"Validado por: {nombre}.")
        if fecha_txt:
            partes.append(f"Fecha de validación: {fecha_txt}.")
        flow.append(Paragraph(" ".join(partes), styles["validation_block"]))
    flow.append(
        Paragraph(
            "H = valor por encima del rango de referencia · L = valor por debajo · * = valor crítico",
            styles["legend"],
        )
    )
    return flow


def construir_story_icpl(
    solicitud: SolicitudExamen,
    resultados: list[ResultadoExamen],
    *,
    estudios_micro: list | None = None,
) -> list[Any]:
    styles = _styles()
    story: list[Any] = []
    es_parcial = (
        solicitud.estado == "INFORMADO_PARCIAL"
        or not solicitud_resultados_completos(solicitud)
    )
    if es_parcial:
        story.append(
            Paragraph(
                "INFORME PARCIAL — algunos resultados están pendientes de completar o validar.",
                styles["partial_banner"],
            )
        )
        story.append(Spacer(1, 0.15 * cm))
    elif solicitud.estado != "FINALIZADO":
        story.append(
            Paragraph(
                "BORRADOR — resultados aún no validados para emisión oficial.",
                styles["partial_banner"],
            )
        )
        story.append(Spacer(1, 0.15 * cm))

    grupos = agrupar_resultados_por_panel(solicitud, resultados)
    obs = (getattr(solicitud, "observaciones", None) or "").strip()
    conclusion_hemo_insertada = False

    if not grupos:
        story.append(Paragraph("Sin resultados registrados.", styles["empty"]))
    else:
        for grupo in grupos:
            story.extend(_bloque_panel(grupo, styles))
            if obs and grupo.panel_codigo == PANEL_HEMOGRAMA and not conclusion_hemo_insertada:
                story.append(Spacer(1, 0.2 * cm))
                story.append(
                    Paragraph("CONCLUSIÓN / OBSERVACIONES (HEMOGRAMA)", styles["observaciones_title"])
                )
                story.append(
                    Paragraph(_escape(obs).replace("\n", "<br/>"), styles["observaciones"])
                )
                conclusion_hemo_insertada = True

    if estudios_micro:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("MICROBIOLOGÍA", styles["panel"]))
        for est in estudios_micro:
            story.append(
                Paragraph(
                    _escape(
                        f"{est.numero or est.pk} — {est.get_tipo_estudio_display()} — "
                        f"{est.get_estado_display()}"
                    ),
                    styles["exam_meta"],
                )
            )

    if obs and not conclusion_hemo_insertada:
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph("CONCLUSIÓN / OBSERVACIONES", styles["observaciones_title"]))
        story.append(Paragraph(_escape(obs).replace("\n", "<br/>"), styles["observaciones"]))

    story.extend(_bloque_validacion(solicitud, resultados, styles))
    return story


def preparar_contexto_encabezado(solicitud: SolicitudExamen) -> dict[str, Any]:
    paciente = solicitud.paciente
    procedencia = resolver_procedencia_solicitud(solicitud)
    solicitado, derivante = _derivante_y_solicitante(procedencia)
    hc = ""
    if solicitud.consulta_hc_id:
        hc = str(solicitud.consulta_hc_id)

    return {
        "protocolo": _protocolo_display(solicitud.numero, solicitud.pk),
        "solicitado_por": solicitado,
        "derivante": derivante,
        "fecha": formatear_fecha_larga(solicitud.fecha_solicitud),
        "paciente": formatear_paciente_apellido_nombre(paciente),
        "historia_clinica": hc or "—",
        "documento": str(getattr(paciente, "dni", "") or "—"),
        "fecha_nac": formatear_edad_paciente(paciente),
    }


def generar_pdf_icpl_bytes(
    solicitud: SolicitudExamen,
    resultados: list[ResultadoExamen],
    *,
    estudios_micro: list | None = None,
) -> bytes:
    buffer = BytesIO()
    ctx = preparar_contexto_encabezado(solicitud)
    doc = _InformeIcplDoc(
        buffer,
        ctx,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=HEADER_HEIGHT + CONTENT_TOP_PAD,
        bottomMargin=1.0 * cm,
        title=f"Informe {ctx['protocolo']}",
    )
    story = construir_story_icpl(solicitud, resultados, estudios_micro=estudios_micro)
    doc.build(story)
    return buffer.getvalue()


def generar_pdf_icpl_desde_contexto(ctx: dict[str, Any], story: list[Any]) -> bytes:
    """PDF con encabezado/pie ICPL y cuerpo arbitrario (p. ej. informe micro)."""
    buffer = BytesIO()
    doc = _InformeIcplDoc(
        buffer,
        ctx,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=HEADER_HEIGHT + CONTENT_TOP_PAD,
        bottomMargin=1.0 * cm,
        title=f"Informe {ctx.get('protocolo') or ''}".strip(),
    )
    doc.build(story)
    return buffer.getvalue()


def estilos_informe_icpl() -> dict[str, ParagraphStyle]:
    """Estilos tipográficos del informe (reutilizables fuera del layout LIMS)."""
    return _styles()


def escape_texto_informe(text: str) -> str:
    return _escape(text)
