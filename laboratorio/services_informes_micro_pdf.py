"""
PDF de informe microbiológico clínico — generación en memoria (formato ICPL).

Vista derivada. No modifica estado ni persiste archivos.
Requiere informe FINAL en estado EMITIDO o VALIDADO.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from auditoria.audit_service import log_event
from laboratorio.informe_pdf_layout import (
    escape_texto_informe,
    estilos_informe_icpl,
    formatear_edad_paciente,
    formatear_fecha_larga,
    formatear_paciente_apellido_nombre,
    generar_pdf_icpl_desde_contexto,
)
from laboratorio.models_microbiologia import (
    Antibiograma,
    EstudioMicrobiologia,
    InformeMicrobiologia,
    LecturaCultivo,
)


class InformeMicroPdfError(ValueError):
    """No se puede generar el PDF del estudio micro."""


ESTADOS_INFORME_FINAL_ENTREGABLE = frozenset({"EMITIDO", "VALIDADO"})


def nombre_archivo_pdf_micro(estudio_id: int) -> str:
    return f"informe-micro-{estudio_id}.pdf"


def informe_final_entregable(estudio: EstudioMicrobiologia) -> InformeMicrobiologia | None:
    return (
        InformeMicrobiologia.objects.filter(
            estudio_id=estudio.pk,
            tipo="FINAL",
            estado__in=ESTADOS_INFORME_FINAL_ENTREGABLE,
        )
        .order_by("-fecha_validacion", "-fecha_emision", "-pk")
        .first()
    )


def assert_estudio_puede_generar_pdf(estudio: EstudioMicrobiologia) -> InformeMicrobiologia:
    if estudio.estado == "CANCELADO":
        raise InformeMicroPdfError("El estudio está cancelado.")
    informe = informe_final_entregable(estudio)
    if informe is None:
        raise InformeMicroPdfError(
            "Se requiere un informe FINAL emitido o validado para generar el PDF."
        )
    return informe


def _cargar_estudio(estudio_id: int) -> EstudioMicrobiologia:
    return (
        EstudioMicrobiologia.objects.select_related(
            "paciente",
            "medico_interno",
            "medico_interno__user",
            "tipo_cultivo",
            "tipo_muestra_micro",
            "solicitud",
            "consulta_hc",
        )
        .prefetch_related(
            "lecturas",
            "siembras__medio",
            "aislados__microorganismo",
            "aislados__antibiogramas__resultados__antibiotico",
            "aislados__identificaciones__microorganismo",
            "informes",
        )
        .get(pk=estudio_id)
    )


def _medico_label(estudio: EstudioMicrobiologia) -> str:
    mi = estudio.medico_interno
    if mi is not None:
        parts = [getattr(mi, "apellido", "") or "", getattr(mi, "nombre", "") or ""]
        label = ", ".join(x for x in parts if x).strip(", ")
        if label:
            return f"Dr. {label}"
        return str(mi)
    ext = (estudio.medico_externo_nombre or "").strip()
    if ext:
        return ext
    sol = estudio.solicitud
    if sol is not None:
        mi = getattr(sol, "medico_interno", None)
        if mi is not None:
            parts = [getattr(mi, "apellido", "") or "", getattr(mi, "nombre", "") or ""]
            label = ", ".join(x for x in parts if x).strip(", ")
            if label:
                return f"Dr. {label}"
        return (getattr(sol, "medico_externo_nombre", None) or "").strip() or "—"
    return "—"


def _cultivo_label(estudio: EstudioMicrobiologia) -> str:
    if estudio.tipo_cultivo_id and estudio.tipo_cultivo:
        return estudio.tipo_cultivo.nombre
    return (estudio.tipo_estudio or "—").replace("_", " ")


def _muestra_label(estudio: EstudioMicrobiologia) -> str:
    if estudio.tipo_muestra_micro_id and estudio.tipo_muestra_micro:
        return estudio.tipo_muestra_micro.nombre
    return "—"


def _protocolo(estudio: EstudioMicrobiologia) -> str:
    numero = (estudio.numero or "").strip()
    if not numero:
        return str(estudio.pk)
    parts = numero.split("-")
    if len(parts) >= 3 and parts[-1].isdigit():
        return str(int(parts[-1]))
    return numero


def preparar_contexto_encabezado_micro(estudio: EstudioMicrobiologia) -> dict[str, Any]:
    paciente = estudio.paciente
    fecha_ref = (
        estudio.fecha_cierre
        or estudio.fecha_inicio
        or getattr(estudio, "created_at", None)
        or timezone.now()
    )
    hc = str(estudio.consulta_hc_id) if estudio.consulta_hc_id else "—"
    return {
        "protocolo": _protocolo(estudio),
        "solicitado_por": _medico_label(estudio),
        "derivante": "Microbiología",
        "fecha": formatear_fecha_larga(fecha_ref),
        "paciente": formatear_paciente_apellido_nombre(paciente) if paciente else "—",
        "historia_clinica": hc,
        "documento": str(getattr(paciente, "dni", "") or "—") if paciente else "—",
        "fecha_nac": formatear_edad_paciente(paciente) if paciente else "—",
    }


def _construir_story_micro(
    estudio: EstudioMicrobiologia,
    informe: InformeMicrobiologia,
) -> list[Any]:
    styles = estilos_informe_icpl()
    esc = escape_texto_informe
    story: list[Any] = []

    if estudio.estado not in ("VALIDADO", "INFORMADO"):
        story.append(
            Paragraph(
                "INFORME EMITIDO — pendiente de validación bioquímica / cierre.",
                styles["partial_banner"],
            )
        )
        story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("ESTUDIO MICROBIOLÓGICO", styles["panel"]))
    meta_lines = [
        f"Número: {esc(estudio.numero or f'#{estudio.pk}')}",
        f"Cultivo: {esc(_cultivo_label(estudio))}",
        f"Muestra: {esc(_muestra_label(estudio))}",
        f"Estado estudio: {esc(estudio.get_estado_display())}",
        f"Informe: FINAL — {esc(informe.get_estado_display())}",
    ]
    for line in meta_lines:
        story.append(Paragraph(line, styles["exam_meta"]))
    story.append(Spacer(1, 0.2 * cm))

    # Lecturas
    lecturas = list(
        LecturaCultivo.objects.filter(estudio_id=estudio.pk)
        .select_related("siembra", "siembra__medio")
        .order_by("pk")
    )
    story.append(Paragraph("LECTURAS DE CULTIVO", styles["panel"]))
    if not lecturas:
        story.append(Paragraph("Sin lecturas registradas.", styles["empty"]))
    else:
        header = [
            Paragraph("Siembra / medio", styles["table_header"]),
            Paragraph("Crecimiento", styles["table_header"]),
            Paragraph("Gram / colonias", styles["table_header"]),
        ]
        rows = [header]
        for lec in lecturas:
            medio = ""
            if lec.siembra_id and getattr(lec.siembra, "medio", None):
                medio = lec.siembra.medio.nombre or lec.siembra.medio.codigo or ""
            medio_lbl = f"#{lec.siembra_id} {medio}".strip()
            detalle = " · ".join(
                x
                for x in [
                    (lec.tincion_gram or "").strip(),
                    (lec.descripcion_colonias or "").strip(),
                ]
                if x
            ) or "—"
            rows.append(
                [
                    Paragraph(esc(medio_lbl), styles["exam_meta"]),
                    Paragraph(esc(lec.crecimiento or "—"), styles["exam_title"]),
                    Paragraph(esc(detalle), styles["exam_meta"]),
                ]
            )
        table = Table(rows, colWidths=[5.5 * cm, 4.0 * cm, 7.7 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E5E7EB")),
                ]
            )
        )
        story.append(table)
    story.append(Spacer(1, 0.25 * cm))

    # Aislados
    aislados = [
        a
        for a in estudio.aislados.all()
        if a.estado != "DESCARTADO"
    ]
    story.append(Paragraph("AISLADOS E IDENTIFICACIÓN", styles["panel"]))
    if not aislados:
        story.append(Paragraph("Sin aislados vigentes.", styles["empty"]))
    else:
        for a in aislados:
            micro = a.microorganismo
            if micro is None:
                ident = a.identificaciones.order_by("-pk").first()
                micro = ident.microorganismo if ident else None
            micro_lbl = "—"
            if micro is not None:
                micro_lbl = f"{micro.codigo} — {micro.nombre}".strip(" —")
            story.append(
                Paragraph(
                    esc(
                        f"Aislado #{a.pk} · {a.estado} · {micro_lbl} · "
                        f"Significancia: {a.significancia or '—'}"
                    ),
                    styles["exam_meta"],
                )
            )
    story.append(Spacer(1, 0.25 * cm))

    # Antibiogramas completos
    story.append(Paragraph("ANTIBIOGRAMA", styles["panel"]))
    abs_completos = list(
        Antibiograma.objects.filter(
            aislado__estudio_id=estudio.pk,
            estado="COMPLETO",
        )
        .select_related("aislado", "aislado__microorganismo")
        .prefetch_related("resultados__antibiotico")
        .order_by("pk")
    )
    if not abs_completos:
        story.append(Paragraph("Sin antibiogramas completos.", styles["empty"]))
    else:
        for ab in abs_completos:
            aislado = ab.aislado
            micro = aislado.microorganismo if aislado else None
            micro_lbl = (
                f"{micro.codigo} — {micro.nombre}" if micro else f"Aislado #{aislado.pk}"
            )
            story.append(
                Paragraph(
                    esc(f"Antibiograma #{ab.pk} · {micro_lbl}"),
                    styles["exam_title"],
                )
            )
            resultados = list(ab.resultados.all())
            if not resultados:
                story.append(Paragraph("Sin resultados cargados.", styles["empty"]))
                continue
            header = [
                Paragraph("Antibiótico", styles["table_header"]),
                Paragraph("MIC", styles["table_header"]),
                Paragraph("Interp.", styles["table_header"]),
            ]
            rows = [header]
            for r in resultados:
                abio = r.antibiotico
                nom = (
                    f"{abio.codigo} — {abio.nombre}" if abio else str(r.antibiotico_id)
                )
                rows.append(
                    [
                        Paragraph(esc(nom), styles["exam_meta"]),
                        Paragraph(esc(r.mic or "—"), styles["exam_meta"]),
                        Paragraph(esc(r.interpretacion or "—"), styles["exam_title"]),
                    ]
                )
            table = Table(rows, colWidths=[10.0 * cm, 3.5 * cm, 3.7 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E5E7EB")),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.15 * cm))

    # Texto informe
    texto = (informe.texto or "").strip()
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("INFORME / CONCLUSIÓN", styles["observaciones_title"]))
    if texto:
        story.append(
            Paragraph(esc(texto).replace("\n", "<br/>"), styles["observaciones"])
        )
    else:
        story.append(Paragraph("Sin texto de informe.", styles["empty"]))

    obs = (estudio.observaciones or "").strip()
    if obs:
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph("OBSERVACIONES DEL ESTUDIO", styles["observaciones_title"]))
        story.append(
            Paragraph(esc(obs).replace("\n", "<br/>"), styles["observaciones"])
        )

    return story


def generar_informe_micro_pdf_bytes(estudio: EstudioMicrobiologia) -> bytes:
    """Construye PDF en memoria del estudio micro con informe FINAL entregable."""
    estudio = _cargar_estudio(estudio.pk)
    informe = assert_estudio_puede_generar_pdf(estudio)
    ctx = preparar_contexto_encabezado_micro(estudio)
    story = _construir_story_micro(estudio, informe)
    return generar_pdf_icpl_desde_contexto(ctx, story)


def auditar_descarga_informe_micro_pdf(*, actor, estudio: EstudioMicrobiologia) -> None:
    log_event(
        action="UPDATE",
        actor=actor,
        entity=estudio,
        entity_repr=f"laboratorio.EstudioMicrobiologia:{estudio.pk}",
        after=None,
        module="laboratorio",
        metadata={
            "accion": "lims_micro_informe_pdf_download",
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
            "view": "EstudioMicrobiologiaViewSet.informe_pdf",
        },
    )
