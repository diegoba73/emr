"""
LIMS PDF — generación en memoria de informe por solicitud (formato ICPL fase 1).

Vista derivada (no fuente primaria). No modifica estado ni persiste archivos.
"""
from __future__ import annotations

import re
from typing import Any

from auditoria.audit_service import log_event
from laboratorio.informe_pdf_layout import generar_pdf_icpl_bytes
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.models_microbiologia import EstudioMicrobiologia


def nombre_archivo_pdf_seguro(solicitud_id: int) -> str:
    """Nombre de descarga sin PHI ni DNI."""
    return f"informe-lims-solicitud-{solicitud_id}.pdf"


def _cargar_datos_solicitud(solicitud: SolicitudExamen) -> dict[str, Any]:
    solicitud = (
        SolicitudExamen.objects.select_related(
            "paciente",
            "medico_interno",
            "consulta_hc__turno__recurso",
        )
        .prefetch_related(
            "resultados__tipo_examen__tipo_muestra_requerida",
            "resultados__muestra__tipo_muestra",
            "paneles__tipos_examen",
            "tipos_examen",
        )
        .get(pk=solicitud.pk)
    )
    resultados = list(
        solicitud.resultados.all().order_by("tipo_examen__nombre", "pk")
    )
    muestras = list(
        Muestra.objects.filter(solicitud_id=solicitud.pk)
        .select_related("tipo_muestra")
        .order_by("pk")
    )
    estudios_micro = list(
        EstudioMicrobiologia.objects.filter(solicitud_id=solicitud.pk)
        .prefetch_related("siembras__medio", "siembras__lecturas", "informes")
        .order_by("pk")
    )
    return {
        "solicitud": solicitud,
        "resultados": resultados,
        "muestras": muestras,
        "estudios_micro": estudios_micro,
    }


def generar_informe_lims_pdf_bytes(
    solicitud: SolicitudExamen,
    *,
    role: str,
) -> bytes:
    """Construye PDF en memoria con layout ICPL (paneles, encabezado institucional)."""
    datos = _cargar_datos_solicitud(solicitud)
    return generar_pdf_icpl_bytes(
        datos["solicitud"],
        datos["resultados"],
        estudios_micro=datos["estudios_micro"],
    )


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
