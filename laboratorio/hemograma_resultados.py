"""
Asegura filas ResultadoExamen faltantes cuando el catálogo del panel crece
(p. ej. HCM / VLDL / BIL_I agregados a órdenes ya abiertas).
"""
from __future__ import annotations

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.orden_grupos_informe import PANEL_HEMOGRAMA
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO

_ESTADOS_ABIERTOS = frozenset(
    {"PENDIENTE", "EN_PROCESO", "INFORMADO_PARCIAL", "LISTO_PARA_VALIDAR"}
)
_PANELES_ASEGURAR = frozenset({"PAN_HEMO", "PAN_LIP", "PAN_HEP"})


def _asegurar_codigos_panel(solicitud: SolicitudExamen, panel_codigo: str) -> int:
    codigos_panel = list(PANEL_COMPONENTES_BY_CODIGO.get(panel_codigo) or [])
    if not codigos_panel:
        return 0

    tiene_panel = False
    try:
        tiene_panel = solicitud.paneles.filter(codigo=panel_codigo).exists()
    except Exception:
        tiene_panel = False

    existentes = {
        (getattr(te, "codigo", None) or "").strip().upper()
        for te in TipoExamen.objects.filter(
            id__in=solicitud.resultados.values_list("tipo_examen_id", flat=True)
        )
    }
    if not tiene_panel:
        if not (existentes & set(codigos_panel)):
            return 0

    faltan = [c for c in codigos_panel if c and c not in existentes]
    if not faltan:
        return 0

    tipos = {
        te.codigo: te
        for te in TipoExamen.objects.filter(codigo__in=faltan, activo=True)
    }
    creados = 0
    for codigo in faltan:
        te = tipos.get(codigo)
        if te is None:
            continue
        _, was_created = ResultadoExamen.objects.get_or_create(
            solicitud=solicitud,
            tipo_examen=te,
            defaults={"valor_obtenido": ""},
        )
        if was_created:
            creados += 1
            if not solicitud.tipos_examen.filter(pk=te.pk).exists():
                solicitud.tipos_examen.add(te)
    return creados


def asegurar_resultados_panel_hemograma(solicitud: SolicitudExamen) -> int:
    """Compat: asegura componentes del hemograma (incluye HCM)."""
    if getattr(solicitud, "estado", None) not in _ESTADOS_ABIERTOS:
        return 0
    return _asegurar_codigos_panel(solicitud, PANEL_HEMOGRAMA)


def asegurar_resultados_paneles_derivados(solicitud: SolicitudExamen) -> int:
    """Asegura componentes de hemograma, perfil lipidico y hepatograma."""
    if getattr(solicitud, "estado", None) not in _ESTADOS_ABIERTOS:
        return 0
    total = 0
    for codigo in _PANELES_ASEGURAR:
        total += _asegurar_codigos_panel(solicitud, codigo)
    return total
