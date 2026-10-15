"""
Cabecera clínica de una orden LIMS: fecha de extracción y diagnóstico.

Fuentes:
- Fecha solicitud: SolicitudExamen.fecha_solicitud.
- Fecha extracción (orden): max(Muestra.fecha_toma); si no hay toma, fecha_programada_toma.
- Fecha extracción (determinación): ResultadoExamen.muestra.fecha_toma; si no hay FK,
  tubo compatible de la orden por tipo de muestra; si no, programada de la orden.
- Diagnóstico internado: Internacion activa (CIE o texto de ingreso), como en cama.
- Diagnóstico guardia: motivo cargado en la atención (observaciones_generales) o
  motivo_consulta_detalle de la consulta HC (omite stub genérico).
- Diagnóstico ambulatorio: consulta HC vinculada; si no, antecedentes personales del paciente.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Iterable

from django.utils import timezone

if TYPE_CHECKING:
    from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen
    from laboratorio.models_catalog import Muestra

# Motivo placeholder al crear Consulta HC de guardia sin texto clínico real.
_MOTIVOS_GUARDIA_STUB = frozenset(
    {
        "guardia cardiológica",
        "guardia",
        "consulta médica",
    }
)


def fecha_solicitud_dt(solicitud: SolicitudExamen) -> datetime | date | None:
    return getattr(solicitud, "fecha_solicitud", None) or getattr(
        solicitud, "created_at", None
    )


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


def fecha_solicitud_display(solicitud: SolicitudExamen) -> str:
    return formatear_fecha_extraccion(fecha_solicitud_dt(solicitud)) or "—"


def _muestras_de_solicitud(
    solicitud: SolicitudExamen,
    muestras: Iterable["Muestra"] | None = None,
) -> list["Muestra"]:
    if muestras is not None:
        return list(muestras)
    rel = getattr(solicitud, "muestras", None)
    if rel is None:
        return []
    try:
        return list(rel.all())
    except Exception:
        return list(rel) if isinstance(rel, (list, tuple)) else []


def fecha_extraccion_dt(solicitud: SolicitudExamen) -> datetime | date | None:
    """Datetime/date canónica de extracción para la orden (sin formatear)."""
    fechas = [
        m.fecha_toma
        for m in _muestras_de_solicitud(solicitud)
        if getattr(m, "fecha_toma", None)
    ]
    if fechas:
        return max(fechas)
    prog = getattr(solicitud, "fecha_programada_toma", None)
    return prog or None


def fecha_extraccion_display(solicitud: SolicitudExamen) -> str:
    return formatear_fecha_extraccion(fecha_extraccion_dt(solicitud)) or "—"


def _fecha_toma_muestra_compatible(
    tipo_examen: "TipoExamen",
    muestras: Iterable["Muestra"],
) -> datetime | None:
    """Mejor fecha_toma entre tubos de la orden compatibles con el examen."""
    from laboratorio.resultado_muestra_validacion import (
        tipo_muestra_fisica_compatible_con_examen,
    )

    candidatas = [
        m.fecha_toma
        for m in muestras
        if getattr(m, "fecha_toma", None)
        and tipo_muestra_fisica_compatible_con_examen(tipo_examen, m)
    ]
    if not candidatas:
        return None
    return max(candidatas)


def fecha_extraccion_de_tipo_examen_dt(
    tipo_examen: "TipoExamen | None",
    solicitud: SolicitudExamen,
    *,
    muestras: Iterable["Muestra"] | None = None,
) -> datetime | date | None:
    """Extracción para un tipo de examen (sin ResultadoExamen), p. ej. ítems del talón."""
    if tipo_examen is None:
        return fecha_extraccion_dt(solicitud)
    lista = _muestras_de_solicitud(solicitud, muestras)
    tomada = _fecha_toma_muestra_compatible(tipo_examen, lista)
    if tomada is not None:
        return tomada
    prog = getattr(solicitud, "fecha_programada_toma", None)
    return prog or None


def fecha_extraccion_de_resultado_dt(
    resultado: "ResultadoExamen",
    *,
    muestras: Iterable["Muestra"] | None = None,
) -> datetime | date | None:
    """
    Extracción de la determinación: tubo vinculado, o tubo compatible de la orden,
    o fecha programada / agregada de la solicitud.
    """
    muestra = getattr(resultado, "muestra", None)
    if muestra is not None and getattr(muestra, "fecha_toma", None):
        return muestra.fecha_toma

    solicitud = getattr(resultado, "solicitud", None)
    tipo_examen = getattr(resultado, "tipo_examen", None)
    if solicitud is None:
        return None

    lista = _muestras_de_solicitud(solicitud, muestras)
    if tipo_examen is not None:
        tomada = _fecha_toma_muestra_compatible(tipo_examen, lista)
        if tomada is not None:
            return tomada

    return fecha_extraccion_dt(solicitud)


def fecha_extraccion_de_resultado_display(
    resultado: "ResultadoExamen",
    *,
    muestras: Iterable["Muestra"] | None = None,
) -> str:
    return (
        formatear_fecha_extraccion(
            fecha_extraccion_de_resultado_dt(resultado, muestras=muestras)
        )
        or "—"
    )


def fechas_extraccion_distintas_en_orden(
    solicitud: SolicitudExamen,
    *,
    muestras: Iterable["Muestra"] | None = None,
) -> bool:
    """True si hay más de una fecha_toma distinta entre tubos de la orden."""
    claves: set[str] = set()
    for m in _muestras_de_solicitud(solicitud, muestras):
        ft = getattr(m, "fecha_toma", None)
        if not ft:
            continue
        claves.add(formatear_fecha_extraccion(ft))
    return len(claves) > 1


def lineas_extraccion_timeline(
    solicitud: SolicitudExamen,
    *,
    muestras: Iterable["Muestra"] | None = None,
) -> list[str]:
    """
    Líneas de extracción para timeline Paciente 360.

    - Un solo material tomado → ``Extracción: DD/MM/YYYY HH:MM``.
    - Varios materiales (sangre + orina, etc.) → una línea por material.
    - Sin toma física → fecha programada si existe.
    """
    por_material: dict[str, datetime] = {}
    for m in _muestras_de_solicitud(solicitud, muestras):
        ft = getattr(m, "fecha_toma", None)
        if not ft:
            continue
        tm = getattr(m, "tipo_muestra", None)
        nombre = (getattr(tm, "nombre", None) or "").strip() or "Muestra"
        prev = por_material.get(nombre)
        if prev is None or ft > prev:
            por_material[nombre] = ft

    if not por_material:
        prog = getattr(solicitud, "fecha_programada_toma", None)
        if prog:
            return [f"Extracción: {formatear_fecha_extraccion(prog)} (programada)"]
        return []

    if len(por_material) == 1:
        ft = next(iter(por_material.values()))
        return [f"Extracción: {formatear_fecha_extraccion(ft)}"]

    return [
        f"Extracción {nombre.lower()}: {formatear_fecha_extraccion(ft)}"
        for nombre, ft in sorted(por_material.items(), key=lambda kv: kv[1])
    ]


def lineas_fechas_orden_timeline(
    solicitud: SolicitudExamen,
    *,
    muestras: Iterable["Muestra"] | None = None,
) -> list[str]:
    """Solicitud + extracción(es) para la tarjeta de timeline."""
    lines: list[str] = []
    sol = fecha_solicitud_display(solicitud)
    if sol and sol != "—":
        lines.append(f"Solicitud: {sol}")
    lines.extend(lineas_extraccion_timeline(solicitud, muestras=muestras))
    return lines


def lineas_fechas_estudio_micro_timeline(estudio) -> list[str]:
    """Solicitud + extracción para timeline de un estudio de microbiología."""
    lines: list[str] = []
    sol = formatear_fecha_extraccion(getattr(estudio, "created_at", None))
    if sol:
        lines.append(f"Solicitud: {sol}")
    if getattr(estudio, "fecha_inicio", None):
        lines.append(
            f"Extracción: {formatear_fecha_extraccion(estudio.fecha_inicio)}"
        )
    else:
        prog = getattr(estudio, "fecha_programada_toma", None)
        if prog:
            lines.append(
                f"Extracción: {formatear_fecha_extraccion(prog)} (programada)"
            )
    return lines


def _fecha_ref_diagnostico(obj: Any) -> datetime | date:
    return (
        getattr(obj, "fecha_solicitud", None)
        or getattr(obj, "created_at", None)
        or timezone.now()
    )


def _diagnostico_internacion(solicitud: Any) -> str:
    from internacion.models import Internacion

    paciente_id = getattr(solicitud, "paciente_id", None)
    if not paciente_id:
        return ""
    internacion = (
        Internacion.objects.filter(
            paciente_id=paciente_id,
            activo=True,
            fecha_ingreso__lte=_fecha_ref_diagnostico(solicitud),
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
    texto = (internacion.diagnostico_ingreso or "").strip()
    if texto:
        return texto
    return (internacion.motivo_ingreso or "").strip()


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


def _motivo_guardia_texto(texto: str | None) -> str:
    t = (texto or "").strip()
    if not t:
        return ""
    if t.casefold() in _MOTIVOS_GUARDIA_STUB:
        return ""
    return t


def _diagnostico_guardia(solicitud: Any) -> str:
    """Motivo de guardia: atención.observaciones_generales → consulta.motivo."""
    from laboratorio.origen_solicitud import _atencion_desde_consulta

    consulta = getattr(solicitud, "consulta_hc", None)
    atencion = _atencion_desde_consulta(consulta)
    if atencion is not None:
        motivo = _motivo_guardia_texto(
            getattr(atencion, "observaciones_generales", None)
        )
        if motivo:
            return motivo
    if consulta is not None:
        motivo = _motivo_guardia_texto(
            getattr(consulta, "motivo_consulta_detalle", None)
        )
        if motivo:
            return motivo
    return ""


def _es_contexto_internacion(solicitud: Any, procedencia_tipo: str | None) -> bool:
    if procedencia_tipo == "INTERNACION":
        return True
    origen = (getattr(solicitud, "origen_solicitud", None) or "").strip()
    return origen.startswith("INTERNACION")


def _es_contexto_guardia(solicitud: Any, procedencia_tipo: str | None) -> bool:
    if procedencia_tipo == "GUARDIA":
        return True
    origen = (getattr(solicitud, "origen_solicitud", None) or "").strip()
    return origen == "GUARDIA"


def diagnostico_orden_display(solicitud: Any) -> str:
    """
    Diagnóstico para cabecera / carga de resultados / pedidos impresos.

    Internación → cama/internación activa (CIE, texto ingreso o motivo).
    Guardia → motivo cargado en la atención / consulta.
    Ambulatorio / resto → consulta HC; si no hay, antecedentes del paciente.
    """
    from laboratorio.procedencia_display import resolver_procedencia_solicitud

    procedencia = resolver_procedencia_solicitud(solicitud)
    procedencia_tipo = procedencia.get("procedencia_tipo")

    if _es_contexto_internacion(solicitud, procedencia_tipo):
        dx = _diagnostico_internacion(solicitud)
        if dx:
            return dx

    if _es_contexto_guardia(solicitud, procedencia_tipo):
        dx = _diagnostico_guardia(solicitud)
        if dx:
            return dx

    consulta = getattr(solicitud, "consulta_hc", None)
    dx = _diagnostico_consulta(consulta)
    if dx:
        return dx

    return _diagnostico_paciente(getattr(solicitud, "paciente", None)) or "—"


def diagnostico_para_impresion(obj: Any) -> str:
    """Texto de diagnóstico para PDF de pedidos (vacío si no hay dato)."""
    sol = getattr(obj, "solicitud", None)
    if sol is not None and getattr(obj, "solicitud_id", None):
        obj = sol
    dx = diagnostico_orden_display(obj)
    return "" if dx in ("", "—") else dx
