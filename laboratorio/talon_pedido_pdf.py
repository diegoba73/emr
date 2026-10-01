"""
Talón PDF de respaldo (hoja común) para pedidos LIMS clínico y microbiología.

Formato físico: un talón por ORDEN (no por tubo). Lista completa de paneles
y exámenes sueltos (sin expandir los componentes de cada perfil). Hasta 15
ítems por columna; si hay más, siguen en la columna siguiente (y página
siguiente si no caben más columnas).
No muta estado ni FSM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from auditoria.audit_service import log_event
from laboratorio.models import SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.models_microbiologia import EstudioMicrobiologia

PAGE_W, PAGE_H = A4
MARGIN_X = 12 * mm
MARGIN_Y = 10 * mm
# Pie con fecha de generación.
FOOTER_RESERVE = 10 * mm
# Lista de paneles/exámenes: como máximo 15 por columna; si hay más, otra columna.
MAX_EXAMENES_POR_COLUMNA = 15
# En A4 caben hasta 3 columnas legibles; el resto sigue en la página siguiente.
MAX_COLUMNAS_POR_PAGINA = 3


def nombre_archivo_talon_solicitud(solicitud: SolicitudExamen) -> str:
    ref = (solicitud.numero or str(solicitud.pk)).replace("/", "-")
    safe = re.sub(r"[^\w.\-]+", "_", ref)[:80]
    return f"talon-orden-{safe}.pdf"


def nombre_archivo_talon_micro(estudio: EstudioMicrobiologia) -> str:
    ref = (estudio.numero or estudio.codigo_barra or str(estudio.pk)).replace("/", "-")
    safe = re.sub(r"[^\w.\-]+", "_", ref)[:80]
    return f"talon-micro-{safe}.pdf"


def _texto(val: Any, default: str = "—") -> str:
    s = (str(val).strip() if val is not None else "") or ""
    return s if s else default


def _trunc(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _fmt_paciente(paciente) -> tuple[str, str]:
    if paciente is None:
        return "—", "—"
    apellido = (getattr(paciente, "apellido", None) or "").strip()
    nombre = (getattr(paciente, "nombre", None) or "").strip()
    if apellido and nombre:
        nombre_completo = f"{apellido}, {nombre}"
    else:
        nombre_completo = apellido or nombre or getattr(paciente, "nombre_completo", None) or "—"
    dni = _texto(getattr(paciente, "dni", None))
    return nombre_completo, dni


def _fmt_medico(medico, externo: str = "") -> str:
    if medico is not None:
        apellido = (getattr(medico, "apellido", None) or "").strip()
        nombre = (getattr(medico, "nombre", None) or "").strip()
        if apellido and nombre:
            name = f"{apellido}, {nombre}"
        else:
            name = apellido or nombre or "—"
        mat = (getattr(medico, "matricula", None) or "").strip()
        if mat and name != "—":
            return f"{name} · MP {mat}"
        if mat:
            return f"MP {mat}"
        return name
    ext = (externo or "").strip()
    return ext if ext else "—"


def _lugar_desde_muestra_o_solicitud(solicitud: SolicitudExamen, muestra: Muestra | None) -> str:
    if muestra is not None:
        lugar = (getattr(muestra, "lugar_extraccion", None) or "").strip()
        if lugar:
            return lugar
    from laboratorio.services_etiqueta_muestra import resolver_lugar_etiqueta_desde_solicitud

    return resolver_lugar_etiqueta_desde_solicitud(solicitud) or "—"


def _examenes_solicitud(solicitud: SolicitudExamen) -> list[str]:
    """Paneles/perfiles como ítem único + exámenes sueltos (sin componentes del panel)."""
    nombres: list[str] = []
    seen: set[str] = set()
    paneles = list(solicitud.paneles.all().order_by("nombre"))
    componentes_panel: set[int] = set()
    for panel in paneles:
        componentes_panel.update(te.pk for te in panel.tipos_examen.all())
        n = (panel.nombre or panel.codigo or "").strip()
        if n and n not in seen:
            seen.add(n)
            nombres.append(n)

    for te in solicitud.tipos_examen.all().order_by("nombre"):
        if te.pk in componentes_panel:
            continue
        n = (te.nombre or te.codigo or "").strip()
        if n and n not in seen:
            seen.add(n)
            nombres.append(n)

    if not nombres:
        for res in solicitud.resultados.select_related("tipo_examen").order_by(
            "tipo_examen__nombre", "pk"
        ):
            te = res.tipo_examen
            if te is None or te.pk in componentes_panel:
                continue
            n = (te.nombre or te.codigo or "").strip()
            if n and n not in seen:
                seen.add(n)
                nombres.append(n)
    return nombres


def _lugar_estudio_micro(estudio: EstudioMicrobiologia) -> str:
    from laboratorio.procedencia_display import resolver_procedencia_solicitud
    from laboratorio.origen_solicitud import label_origen_solicitud

    sol = getattr(estudio, "solicitud", None)
    if sol is not None:
        disp = resolver_procedencia_solicitud(sol).get("procedencia_display") or ""
        if disp.strip() and disp.strip() not in ("—", "-"):
            return disp.strip()

    class _Proxy:
        pass

    proxy = _Proxy()
    proxy.paciente_id = estudio.paciente_id
    proxy.origen_solicitud = getattr(estudio, "origen_solicitud", "") or ""
    proxy.consulta_hc = getattr(estudio, "consulta_hc", None)
    proxy.fecha_solicitud = getattr(estudio, "created_at", None) or timezone.now()
    disp = resolver_procedencia_solicitud(proxy).get("procedencia_display") or ""
    if disp.strip() and disp.strip() not in ("—", "-"):
        return disp.strip()
    return label_origen_solicitud(getattr(estudio, "origen_solicitud", None) or "") or "—"


def _examenes_micro(estudio: EstudioMicrobiologia) -> list[str]:
    items: list[str] = []
    if estudio.tipo_cultivo_id:
        tc = estudio.tipo_cultivo
        n = (tc.nombre or tc.codigo or "").strip() if tc else ""
        if n:
            items.append(f"Cultivo: {n}")
    elif (estudio.tipo_estudio or "").strip():
        items.append(f"Estudio: {estudio.tipo_estudio.strip()}")
    if estudio.tipo_muestra_micro_id:
        tm = estudio.tipo_muestra_micro
        n = (tm.nombre or tm.codigo or "").strip() if tm else ""
        if n:
            items.append(f"Muestra: {n}")
    return items or ["—"]


@dataclass(frozen=True)
class TalonHalfData:
    titulo: str
    numero_pedido: str
    paciente_nombre: str
    dni: str
    lugar: str
    medico: str
    examenes: list[str]
    codigo_barra: str
    tubo_label: str = ""


def _draw_footer(c: canvas.Canvas) -> None:
    c.setFont("Helvetica", 7)
    c.setFillGray(0.4)
    ahora = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")
    c.drawString(MARGIN_X, MARGIN_Y, f"Generado: {ahora}")
    c.setFillGray(0)


def columnas_examenes(
    examenes: list[str],
    *,
    max_por_columna: int = MAX_EXAMENES_POR_COLUMNA,
) -> list[list[str]]:
    """Parte la lista en columnas de a lo sumo ``max_por_columna`` ítems."""
    items = examenes or ["—"]
    if max_por_columna < 1:
        raise ValueError("max_por_columna debe ser >= 1")
    return [items[i : i + max_por_columna] for i in range(0, len(items), max_por_columna)]


def _max_chars_columna(c: canvas.Canvas, col_w: float, font: str = "Helvetica", size: float = 8) -> int:
    """Estima cuántos caracteres entran en el ancho de columna (bullet + margen)."""
    usable = max(col_w - 4 * mm, 10 * mm)
    # Aproximación: medir "M" y acotar.
    mw = c.stringWidth("M", font, size) or 1.0
    return max(8, int(usable / mw))


def _draw_talon_pages(c: canvas.Canvas, data: TalonHalfData) -> None:
    """Dibuja el talón de una orden; exámenes en columnas (máx. 15 c/u)."""
    line = 4.6 * mm
    exam_line = line * 0.92
    examenes = data.examenes or ["—"]
    cols_all = columnas_examenes(examenes)
    page_idx = 0
    col_offset = 0

    while col_offset < len(cols_all):
        if page_idx > 0:
            c.showPage()
        y = PAGE_H - MARGIN_Y
        x = MARGIN_X

        c.setFont("Helvetica-Bold", 11)
        if page_idx == 0:
            c.drawString(x, y, "TALÓN — LABORATORIO (por orden)")
        else:
            c.drawString(x, y, "TALÓN — LABORATORIO (continuación)")
        y -= line * 0.85
        c.setFont("Helvetica", 7.5)
        c.setFillGray(0.35)
        c.drawString(x, y, "Respaldo impresora común · no reemplaza etiqueta de tubo")
        c.setFillGray(0)
        y -= line * 1.05

        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y, _trunc(data.titulo, 70))
        y -= line
        c.setFont("Helvetica", 9)
        pedido = f"Pedido: {_texto(data.numero_pedido)}"
        if data.tubo_label:
            pedido = f"{pedido}  ·  {data.tubo_label}"
        if page_idx > 0:
            pedido = f"{pedido}  ·  pág. {page_idx + 1}"
        c.drawString(x, y, _trunc(pedido, 95))
        y -= line * 1.15

        if page_idx == 0:

            def _campo(label: str, value: str) -> None:
                nonlocal y
                c.setFont("Helvetica-Bold", 8.5)
                c.drawString(x, y, f"{label}:")
                c.setFont("Helvetica", 8.5)
                c.drawString(x + 32 * mm, y, _trunc(value, 78))
                y -= line

            _campo("Paciente", data.paciente_nombre)
            _campo("DNI", data.dni)
            _campo("Lugar", data.lugar)
            _campo("Médico", data.medico)
            _campo("Código", data.codigo_barra or "(sin código aún)")
            y -= line * 0.25

        c.setFont("Helvetica-Bold", 8.5)
        if page_idx == 0:
            c.drawString(x, y, "Exámenes / estudios:")
        else:
            c.drawString(x, y, "Exámenes / estudios (continuación):")
        y -= line

        page_cols = cols_all[col_offset : col_offset + MAX_COLUMNAS_POR_PAGINA]
        n_cols = max(1, len(page_cols))
        usable_w = PAGE_W - 2 * MARGIN_X
        col_w = usable_w / n_cols
        max_chars = _max_chars_columna(c, col_w)
        c.setFont("Helvetica", 8)
        list_top = y
        for ci, col_items in enumerate(page_cols):
            cx = MARGIN_X + ci * col_w
            cy = list_top
            for item in col_items:
                c.drawString(cx + 1.5 * mm, cy, f"• {_trunc(item, max_chars)}")
                cy -= exam_line

        _draw_footer(c)
        col_offset += len(page_cols)
        page_idx += 1


def _render_talones_pdf(talones: list[TalonHalfData]) -> bytes:
    if not talones:
        raise ValueError("Sin datos para talón.")
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i, data in enumerate(talones):
        if i > 0:
            c.showPage()
        _draw_talon_pages(c, data)
    c.save()
    return buf.getvalue()


def _codigo_barra_orden(muestras: list[Muestra]) -> str:
    codigos = [(m.codigo_barra or "").strip() for m in muestras if (m.codigo_barra or "").strip()]
    if not codigos:
        return ""
    if len(codigos) == 1:
        return codigos[0]
    # Varios tubos: listar para referencia; no generar un talón por tubo.
    joined = " · ".join(codigos)
    return _trunc(joined, 90)


def generar_talon_solicitud_pdf_bytes(solicitud: SolicitudExamen) -> bytes:
    """Un talón por orden (todos los paneles/exámenes; 1 PDF page-set, no por tubo)."""
    sol = (
        SolicitudExamen.objects.select_related(
            "paciente",
            "medico_interno",
            "consulta_hc__turno__recurso",
        )
        .prefetch_related(
            "tipos_examen",
            "paneles__tipos_examen",
            "resultados__tipo_examen",
            "muestras__tipo_contenedor",
            "muestras__tipo_muestra",
        )
        .get(pk=solicitud.pk)
    )
    pac_nombre, dni = _fmt_paciente(sol.paciente)
    medico = _fmt_medico(sol.medico_interno)
    examenes = _examenes_solicitud(sol) or ["—"]
    muestras = list(sol.muestras.all().order_by("pk"))
    primera = muestras[0] if muestras else None
    n_tubos = len(muestras)
    tubo_label = ""
    if n_tubos == 1:
        tubo_label = "1 tubo"
    elif n_tubos > 1:
        tubo_label = f"{n_tubos} tubos"

    talon = TalonHalfData(
        titulo="Pedido clínico — talón por orden",
        numero_pedido=sol.numero or str(sol.pk),
        paciente_nombre=pac_nombre,
        dni=dni,
        lugar=_lugar_desde_muestra_o_solicitud(sol, primera),
        medico=medico,
        examenes=examenes,
        codigo_barra=_codigo_barra_orden(muestras),
        tubo_label=tubo_label or ("Sin tubos generados aún" if not muestras else ""),
    )
    return _render_talones_pdf([talon])


def generar_talon_estudio_micro_pdf_bytes(estudio: EstudioMicrobiologia) -> bytes:
    """Un talón por estudio de microbiología (1 muestra de cultivo)."""
    est = (
        EstudioMicrobiologia.objects.select_related(
            "paciente",
            "medico_interno",
            "tipo_cultivo",
            "tipo_muestra_micro",
            "solicitud",
            "consulta_hc__turno__recurso",
        ).get(pk=estudio.pk)
    )
    pac_nombre, dni = _fmt_paciente(est.paciente)
    codigo = (est.codigo_barra or est.numero or "").strip()
    talon = TalonHalfData(
        titulo="Pedido microbiología — talón por orden",
        numero_pedido=est.numero or str(est.pk),
        paciente_nombre=pac_nombre,
        dni=dni,
        lugar=_lugar_estudio_micro(est),
        medico=_fmt_medico(est.medico_interno, getattr(est, "medico_externo_nombre", "") or ""),
        examenes=_examenes_micro(est),
        codigo_barra=codigo,
        tubo_label="Cultivo",
    )
    return _render_talones_pdf([talon])


def auditar_descarga_talon_solicitud(*, actor, solicitud: SolicitudExamen, view: str) -> None:
    log_event(
        action="UPDATE",
        actor=actor,
        entity=solicitud,
        entity_repr=f"laboratorio.SolicitudExamen:{solicitud.pk}",
        after=None,
        module="laboratorio",
        metadata={
            "accion": "talon_pedido_pdf_download",
            "solicitud_id": solicitud.pk,
            "view": view,
        },
    )


def auditar_descarga_talon_micro(*, actor, estudio: EstudioMicrobiologia, view: str) -> None:
    log_event(
        action="UPDATE",
        actor=actor,
        entity=estudio,
        entity_repr=f"laboratorio.EstudioMicrobiologia:{estudio.pk}",
        after=None,
        module="laboratorio",
        metadata={
            "accion": "talon_pedido_pdf_download",
            "estudio_id": estudio.pk,
            "view": view,
        },
    )
