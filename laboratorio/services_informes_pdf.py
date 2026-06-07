"""
LIMS PDF-1 — generación en memoria de informe básico por solicitud.

Vista derivada (no fuente primaria). No modifica estado ni persiste archivos.
"""
from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from auditoria.audit_service import log_event
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.models_microbiologia import (
    EstudioMicrobiologia,
    InformeMicrobiologia,
    LecturaCultivo,
    SiembraMicrobiologia,
)

_INFORME_ESTADOS_VISIBLES_MEDICO = frozenset({"EMITIDO", "VALIDADO"})
_ROLES_OPERACION = frozenset({"admin", "laboratorio"})


def nombre_archivo_pdf_seguro(solicitud_id: int) -> str:
    """Nombre de descarga sin PHI ni DNI."""
    return f"informe-lims-solicitud-{solicitud_id}.pdf"


def _role_es_operacion(role: str) -> bool:
    return role in _ROLES_OPERACION


def _valor_resultado_para_pdf(resultado: ResultadoExamen, role: str) -> str:
    """Incluye valor según visibilidad autorizada por rol."""
    valor = (resultado.valor_obtenido or "").strip()
    if valor:
        return valor
    return "Pendiente"


def _incluir_texto_informe_micro(informe: InformeMicrobiologia, role: str) -> bool:
    if _role_es_operacion(role):
        return bool((informe.texto or "").strip())
    return informe.estado in _INFORME_ESTADOS_VISIBLES_MEDICO and bool(
        (informe.texto or "").strip()
    )


def _cargar_datos_solicitud(solicitud: SolicitudExamen) -> dict[str, Any]:
    solicitud = (
        SolicitudExamen.objects.select_related(
            "paciente",
            "medico_interno",
        )
        .prefetch_related(
            "resultados__tipo_examen",
            "resultados__muestra__tipo_muestra",
            "tipos_examen",
        )
        .get(pk=solicitud.pk)
    )
    muestras = list(
        Muestra.objects.filter(solicitud_id=solicitud.pk)
        .select_related("tipo_muestra")
        .order_by("pk")
    )
    estudios_micro = list(
        EstudioMicrobiologia.objects.filter(solicitud_id=solicitud.pk)
        .prefetch_related(
            "siembras__medio",
            "siembras__lecturas",
            "informes",
        )
        .order_by("pk")
    )
    return {
        "solicitud": solicitud,
        "muestras": muestras,
        "estudios_micro": estudios_micro,
    }


def _escape_pdf_text(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generar_informe_lims_pdf_bytes(
    solicitud: SolicitudExamen,
    *,
    role: str,
) -> bytes:
    """Construye PDF básico en memoria para la solicitud dada."""
    datos = _cargar_datos_solicitud(solicitud)
    sol = datos["solicitud"]
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Informe LIMS solicitud {sol.pk}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LimsTitle",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "LimsSection",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = styles["Normal"]
    small_style = ParagraphStyle(
        "LimsSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
    )

    story: list[Any] = []
    generado_en = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")

    story.append(Paragraph("Informe de Laboratorio — SYNESIS", title_style))
    story.append(Spacer(1, 0.2 * cm))

    encabezado = [
        ["Número de solicitud", _escape_pdf_text(sol.numero or f"ID {sol.pk}")],
        ["Fecha solicitud", sol.fecha_solicitud.strftime("%d/%m/%Y %H:%M")],
        [
            "Paciente",
            _escape_pdf_text(
                sol.paciente.nombre_completo if sol.paciente_id else "—"
            ),
        ],
        ["Médico solicitante", _escape_pdf_text(sol.medico_display)],
        ["Estado solicitud", _escape_pdf_text(sol.get_estado_display())],
        ["Origen", _escape_pdf_text(sol.get_origen_solicitud_display())],
    ]
    if not _role_es_operacion(role) and sol.estado not in ("VALIDADO", "ENTREGADO"):
        encabezado.append(
            [
                "Nota",
                "Documento con resultados en curso; sujeto a validación final.",
            ]
        )

    tabla_enc = Table(encabezado, colWidths=[5.5 * cm, 11 * cm])
    tabla_enc.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tabla_enc)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Resultados", section_style))
    resultados = list(sol.resultados.all().order_by("tipo_examen__nombre", "pk"))
    if resultados:
        filas_res = [["Examen", "Valor", "Unidad", "Estado"]]
        for res in resultados:
            estado_res = "Validado" if res.fecha_validacion else "Pendiente validación"
            filas_res.append(
                [
                    _escape_pdf_text(res.tipo_examen.nombre),
                    _escape_pdf_text(_valor_resultado_para_pdf(res, role)),
                    _escape_pdf_text(res.unidad or res.tipo_examen.unidad_default or "—"),
                    estado_res,
                ]
            )
            if res.muestra_id:
                tm = getattr(res.muestra, "tipo_muestra", None)
                tipo_nom = tm.nombre if tm else "—"
                filas_res.append(
                    [
                        "",
                        f"Muestra asociada: tipo {tipo_nom}, estado {res.muestra.estado}",
                        "",
                        "",
                    ]
                )
        tabla_res = Table(filas_res, colWidths=[5 * cm, 5 * cm, 3 * cm, 3.5 * cm])
        tabla_res.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(tabla_res)
    else:
        story.append(Paragraph("Sin resultados registrados.", body_style))

    muestras: list[Muestra] = datos["muestras"]
    if muestras:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Muestras", section_style))
        filas_m = [["Tipo", "Estado"]]
        for m in muestras:
            filas_m.append(
                [
                    _escape_pdf_text(m.tipo_muestra.nombre),
                    _escape_pdf_text(m.get_estado_display()),
                ]
            )
        tabla_m = Table(filas_m, colWidths=[8 * cm, 8.5 * cm])
        tabla_m.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        story.append(tabla_m)

    estudios: list[EstudioMicrobiologia] = datos["estudios_micro"]
    if estudios:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Microbiología (resumen)", section_style))
        for est in estudios:
            story.append(
                Paragraph(
                    f"Estudio {est.numero or est.pk} — "
                    f"{est.get_tipo_estudio_display()} — "
                    f"Estado: {est.get_estado_display()}",
                    body_style,
                )
            )
            siembras = list(
                SiembraMicrobiologia.objects.filter(estudio_id=est.pk)
                .select_related("medio")
                .order_by("pk")[:5]
            )
            for siem in siembras:
                lecturas = list(
                    LecturaCultivo.objects.filter(siembra_id=siem.pk).order_by("pk")[:3]
                )
                lect_resumen = ", ".join(
                    f"{lec.get_crecimiento_display()}"
                    f"{' (preliminar)' if lec.es_preliminar else ''}"
                    for lec in lecturas
                ) or "sin lecturas"
                story.append(
                    Paragraph(
                        f"  • Siembra: {_escape_pdf_text(siem.medio.nombre)} — "
                        f"lecturas: {_escape_pdf_text(lect_resumen)}",
                        body_style,
                    )
                )
            informes = list(est.informes.all().order_by("tipo", "-pk"))
            for inf in informes:
                linea = (
                    f"  • Informe {inf.get_tipo_display()} — "
                    f"{inf.get_estado_display()}"
                )
                if _incluir_texto_informe_micro(inf, role):
                    texto_corto = (inf.texto or "").strip()
                    if len(texto_corto) > 200:
                        texto_corto = texto_corto[:200] + "…"
                    linea += f": {_escape_pdf_text(texto_corto)}"
                elif inf.estado == "BORRADOR" and not _role_es_operacion(role):
                    linea += " (contenido no disponible)"
                story.append(Paragraph(linea, body_style))
            story.append(Spacer(1, 0.15 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Documento generado por SYNESIS EMR/LIMS — {generado_en}",
            small_style,
        )
    )
    story.append(
        Paragraph(
            "Vista derivada informativa. No reemplaza el registro electrónico "
            "ni constituye informe validado salvo indicación explícita de estado.",
            small_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()


def auditar_descarga_informe_pdf(*, actor, solicitud: SolicitudExamen) -> None:
    """Registra descarga con metadata segura (sin PHI ni codigo_barra)."""
    log_event(
        action="UPDATE",
        actor=actor,
        entity=solicitud,
        entity_repr=f"laboratorio.SolicitudExamen:{solicitud.pk}",
        after=None,
        module="laboratorio",
        metadata={
            "accion": "lims_informe_pdf_download",
            "solicitud_id": solicitud.pk,
            "numero_solicitud": solicitud.numero,
            "view": "SolicitudExamenViewSet.informe_pdf",
        },
    )


def sanitizar_numero_para_filename(numero: str | None) -> str:
    """Por si se usa numero en filename en fases futuras; solo alfanumérico y guión."""
    if not numero:
        return ""
    return re.sub(r"[^A-Za-z0-9\-]", "", str(numero))
