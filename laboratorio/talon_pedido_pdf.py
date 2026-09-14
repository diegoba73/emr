"""
Talón PDF de respaldo (hoja común) para pedidos LIMS clínico y microbiología.

Formato físico: un talón por página, solo en la mitad superior de A4
(media hoja por muestra). Sin copia inferior ni línea de corte.
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

# Un talón = mitad superior de A4 (la inferior queda en blanco).
PAGE_W, PAGE_H = A4
HALF_H = PAGE_H / 2
MARGIN_X = 12 * mm
MARGIN_Y = 8 * mm
# Máximo de líneas de exámenes para que quepa en media hoja.
MAX_EXAMENES_LINES = 8


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
    nombres: list[str] = []
    seen: set[str] = set()
    for panel in solicitud.paneles.all().order_by("nombre"):
        n = (panel.nombre or panel.codigo or "").strip()
        if n and n not in seen:
            seen.add(n)
            nombres.append(f"Panel: {n}")
    for te in solicitud.tipos_examen.all().order_by("nombre"):
        n = (te.nombre or te.codigo or "").strip()
        if n and n not in seen:
            seen.add(n)
            nombres.append(n)
    if not nombres:
        for res in solicitud.resultados.select_related("tipo_examen").order_by(
            "tipo_examen__nombre", "pk"
        ):
            te = res.tipo_examen
            n = (te.nombre or te.codigo or "").strip() if te else ""
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


def _draw_talon_in_half(c: canvas.Canvas, data: TalonHalfData) -> None:
    """Dibuja un único talón en la mitad superior de una hoja A4 (sin marco ni copia)."""
    y0 = HALF_H
    y_top = y0 + HALF_H - MARGIN_Y
    x = MARGIN_X
    line = 4.6 * mm
    y = y_top

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "TALÓN — LABORATORIO (media hoja)")
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
    c.drawString(x, y, _trunc(pedido, 85))
    y -= line * 1.15

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
    c.drawString(x, y, "Exámenes / estudios:")
    y -= line
    c.setFont("Helvetica", 8)
    examenes = data.examenes or ["—"]
    shown = examenes[:MAX_EXAMENES_LINES]
    for item in shown:
        c.drawString(x + 2 * mm, y, f"• {_trunc(item, 90)}")
        y -= line * 0.92
    rest = len(examenes) - len(shown)
    if rest > 0:
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(x + 2 * mm, y, f"… y {rest} más")
        y -= line * 0.9

    c.setFont("Helvetica", 7)
    c.setFillGray(0.4)
    ahora = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")
    # Pie anclado cerca del borde inferior de la mitad
    foot_y = y0 + MARGIN_Y
    c.drawString(x, max(min(y, foot_y + 4 * mm), foot_y), f"Generado: {ahora}")
    c.setFillGray(0)


def _render_talones_pdf(talones: list[TalonHalfData]) -> bytes:
    if not talones:
        raise ValueError("Sin datos para talón.")
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i, data in enumerate(talones):
        if i > 0:
            c.showPage()
        _draw_talon_in_half(c, data)
    c.save()
    return buf.getvalue()


def generar_talon_solicitud_pdf_bytes(solicitud: SolicitudExamen) -> bytes:
    """Un talón (media hoja) por muestra; si no hay tubos, un talón del pedido."""
    sol = (
        SolicitudExamen.objects.select_related(
            "paciente",
            "medico_interno",
            "consulta_hc__turno__recurso",
        )
        .prefetch_related(
            "tipos_examen",
            "paneles",
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

    talones: list[TalonHalfData] = []
    if muestras:
        for idx, m in enumerate(muestras, start=1):
            tc = getattr(m, "tipo_contenedor", None)
            tm = getattr(m, "tipo_muestra", None)
            tubo_bits = []
            if tc and (tc.codigo or tc.nombre):
                tubo_bits.append((tc.codigo or tc.nombre or "").strip())
            elif tm and (tm.codigo or tm.nombre):
                tubo_bits.append((tm.codigo or tm.nombre or "").strip())
            tubo_label = f"Tubo {idx}" + (f" ({', '.join(tubo_bits)})" if tubo_bits else "")
            talones.append(
                TalonHalfData(
                    titulo="Pedido clínico — talón por muestra",
                    numero_pedido=sol.numero or str(sol.pk),
                    paciente_nombre=pac_nombre,
                    dni=dni,
                    lugar=_lugar_desde_muestra_o_solicitud(sol, m),
                    medico=medico,
                    examenes=examenes,
                    codigo_barra=(m.codigo_barra or "").strip(),
                    tubo_label=tubo_label,
                )
            )
    else:
        talones.append(
            TalonHalfData(
                titulo="Pedido clínico — talón por muestra",
                numero_pedido=sol.numero or str(sol.pk),
                paciente_nombre=pac_nombre,
                dni=dni,
                lugar=_lugar_desde_muestra_o_solicitud(sol, None),
                medico=medico,
                examenes=examenes,
                codigo_barra="",
                tubo_label="Sin tubos generados aún",
            )
        )
    return _render_talones_pdf(talones)


def generar_talon_estudio_micro_pdf_bytes(estudio: EstudioMicrobiologia) -> bytes:
    """Un talón media hoja por estudio (1 muestra de cultivo)."""
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
        titulo="Pedido microbiología — talón por muestra",
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
