"""
Asegura filas ResultadoExamen faltantes cuando el catálogo del panel crece
(p. ej. VCM/CHCM agregados a PAN_HEMO en órdenes ya abiertas).
"""
from __future__ import annotations

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.orden_grupos_informe import PANEL_HEMOGRAMA
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO


_ESTADOS_ABIERTOS = frozenset({"PENDIENTE", "EN_PROCESO", "INFORMADO_PARCIAL", "LISTO_PARA_VALIDAR"})


def asegurar_resultados_panel_hemograma(solicitud: SolicitudExamen) -> int:
    """
    Si la orden tiene panel PAN_HEMO (o ya tiene componentes hematológicos) y
    está abierta, crea ResultadoExamen vacíos para códigos del panel que falten.

    Returns:
        Cantidad de filas creadas.
    """
    if getattr(solicitud, "estado", None) not in _ESTADOS_ABIERTOS:
        return 0

    codigos_panel = list(PANEL_COMPONENTES_BY_CODIGO.get(PANEL_HEMOGRAMA) or [])
    if not codigos_panel:
        return 0

    tiene_panel = False
    try:
        tiene_panel = solicitud.paneles.filter(codigo=PANEL_HEMOGRAMA).exists()
    except Exception:
        tiene_panel = False

    existentes = {
        (getattr(te, "codigo", None) or "").strip().upper()
        for te in TipoExamen.objects.filter(
            id__in=solicitud.resultados.values_list("tipo_examen_id", flat=True)
        )
    }
    if not tiene_panel:
        # Órdenes con analitos hemo sueltos (sin panel M2M) también se completan
        # si ya tienen al menos un componente canónico.
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
