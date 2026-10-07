"""
Cabecera clínica de una orden LIMS: fecha de extracción y diagnóstico.

Fuentes:
- Fecha extracción: max(Muestra.fecha_toma); si no hay toma, fecha_programada_toma.
- Diagnóstico internado: Internacion activa (CIE o texto de ingreso), como en cama.
- Diagnóstico ambulatorio: consulta HC vinculada; si no, antecedentes personales del paciente.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from laboratorio.models import SolicitudExamen


def fecha_extraccion_dt(solicitud: SolicitudExamen) -> datetime | date | None:
    """Datetime/date canónica de extracción para la orden (sin formatear)."""
    muestras = getattr(solicitud, "muestras", None)
    if muestras is not None:
        try:
            fechas = [
                m.fecha_toma
                for m in muestras.all()
                if getattr(m, "fecha_toma", None)
            ]
        except Exception:
            fechas = []
        if fechas:
            return max(fechas)
    prog = getattr(solicitud, "fecha_programada_toma", None)
    return prog or None


def formatear_fecha_extraccion(dt: datetime | date | None) -> str:
    """Texto corto para talón / UI: DD/MM/YYYY o DD/MM/YYYY HH:MM."""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
        if local.hour or local.minute or local.second:
            return local.strftime("%d/%m/%Y %H:%M")
        return local.strftime("%d/%m/%Y")
    return dt.strftime("%d/%m/%Y")


def fecha_extraccion_display(solicitud: SolicitudExamen) -> str:
    return formatear_fecha_extraccion(fecha_extraccion_dt(solicitud)) or "—"


def _diagnostico_internacion(solicitud: SolicitudExamen) -> str:
    from internacion.models import Internacion

    internacion = (
        Internacion.objects.filter(
            paciente_id=solicitud.paciente_id,
            activo=True,
            fecha_ingreso__lte=solicitud.fecha_solicitud,
        )
        .select_related("diagnostico_cie")
        .order_by("-fecha_ingreso")
        .first()
    )
    if internacion is None:
        return ""
    cie = getattr(internacion, "diagnostico_cie", None)
    if cie is not None:
        codigo = (getattr(cie, "codigo", None) or "").strip()
        desc = (getattr(cie, "descripcion", None) or "").strip()
        if codigo and desc:
            return f"{codigo} - {desc}"
        return codigo or desc
    return (internacion.diagnostico_ingreso or "").strip()


def _diagnostico_consulta(consulta) -> str:
    if consulta is None:
        return ""
    texto = (getattr(consulta, "diagnostico_presuntivo", None) or "").strip()
    if texto:
        return texto
    try:
        nombres = [
            (d.nombre_diagnostico or "").strip()
            for d in consulta.diagnosticos.all()
        ]
    except Exception:
        nombres = []
    return "; ".join(n for n in nombres if n)


def _diagnostico_paciente(paciente) -> str:
    if paciente is None:
        return ""
    return (getattr(paciente, "antecedentes_personales", None) or "").strip()


def diagnostico_orden_display(solicitud: SolicitudExamen) -> str:
    """
    Diagnóstico para cabecera / carga de resultados.

    Internación → cama/internación activa.
    Ambulatorio / resto → consulta HC; si no hay, datos del paciente (antecedentes).
    """
    from laboratorio.procedencia_display import resolver_procedencia_solicitud

    procedencia = resolver_procedencia_solicitud(solicitud)
    if procedencia.get("procedencia_tipo") == "INTERNACION":
        dx = _diagnostico_internacion(solicitud)
        if dx:
            return dx

    consulta = getattr(solicitud, "consulta_hc", None)
    dx = _diagnostico_consulta(consulta)
    if dx:
        return dx

    return _diagnostico_paciente(getattr(solicitud, "paciente", None)) or "—"
