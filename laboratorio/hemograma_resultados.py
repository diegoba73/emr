"""
Asegura filas ResultadoExamen faltantes cuando el catálogo del panel crece
(p. ej. HCM / VLDL / BIL_I agregados a órdenes ya abiertas).

Solo actúa si el panel está **explícitamente** en la orden. Nunca completa un
panel porque un componente suelto coincida (CREATI ≠ clearance; ionograma al
azar ≠ 24 hs; microalbuminuria al azar ≠ 24 hs).
"""
from __future__ import annotations

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.orden_grupos_informe import PANEL_HEMOGRAMA
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO

_ESTADOS_ABIERTOS = frozenset(
    {"PENDIENTE", "EN_PROCESO", "INFORMADO_PARCIAL", "LISTO_PARA_VALIDAR"}
)

# Paneles cuyo catálogo puede crecer: se reponen componentes faltantes
# únicamente si la orden ya tiene ese panel vinculado.
_PANELES_ASEGURAR = frozenset(
    {
        "PAN_HEMO",
        "PAN_LIP",
        "PAN_HEP",
        "PAN_FERR",
        "PAN_CLEAR",
        "PAN_PROT24",
        "PAN_IONO_U",
        "PAN_IONO_U24",
        "PAN_MALB24",
        "PAN_MALB_AZ",
        "PAN_ENA",
    }
)


def _asegurar_codigos_panel(solicitud: SolicitudExamen, panel_codigo: str) -> int:
    codigos_panel = list(PANEL_COMPONENTES_BY_CODIGO.get(panel_codigo) or [])
    if not codigos_panel:
        return 0

    try:
        tiene_panel = solicitud.paneles.filter(codigo=panel_codigo).exists()
    except Exception:
        tiene_panel = False

    # Sin panel explícito: no expandir por componentes compartidos.
    if not tiene_panel:
        return 0

    existentes = {
        (getattr(te, "codigo", None) or "").strip().upper()
        for te in TipoExamen.objects.filter(
            id__in=solicitud.resultados.values_list("tipo_examen_id", flat=True)
        )
    }

    faltan = [c for c in codigos_panel if c and c not in existentes]
    if not faltan:
        return 0

    from laboratorio.examen_orina_micro import valor_inicial_resultado

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
            defaults={"valor_obtenido": valor_inicial_resultado(te)},
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


def _asegurar_insumos_calculados(solicitud: SolicitudExamen) -> int:
    """Si hay un calculado suelto (p. ej. RAC), crea filas de sus medidos."""
    from laboratorio.calculos_derivados import codigos_insumos_de_calculados
    from laboratorio.examen_orina_micro import valor_inicial_resultado

    existentes = {
        (getattr(te, "codigo", None) or "").strip().upper()
        for te in TipoExamen.objects.filter(
            id__in=solicitud.resultados.values_list("tipo_examen_id", flat=True)
        )
    }
    faltan = codigos_insumos_de_calculados(existentes)
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
            defaults={"valor_obtenido": valor_inicial_resultado(te)},
        )
        if was_created:
            creados += 1
            if not solicitud.tipos_examen.filter(pk=te.pk).exists():
                solicitud.tipos_examen.add(te)
    return creados


def _asegurar_legacy_ena(solicitud: SolicitudExamen) -> int:
    """Si la orden tiene ENA único (legacy), completa PAN_ENA + componentes."""
    from laboratorio.catalogo_solicitud_papel import LEGACY_EXAMEN_A_PANEL
    from laboratorio.models import PanelExamen

    panel_codigo = LEGACY_EXAMEN_A_PANEL.get("ENA")
    if not panel_codigo:
        return 0
    tiene_ena = solicitud.resultados.filter(tipo_examen__codigo="ENA").exists()
    if not tiene_ena:
        return 0
    try:
        panel = PanelExamen.objects.get(codigo=panel_codigo, activo=True)
    except PanelExamen.DoesNotExist:
        return 0
    if not solicitud.paneles.filter(pk=panel.pk).exists():
        solicitud.paneles.add(panel)
    return _asegurar_codigos_panel(solicitud, panel_codigo)


def asegurar_resultados_paneles_derivados(solicitud: SolicitudExamen) -> int:
    """Asegura componentes faltantes de paneles pedidos y de insumos de calculados."""
    if getattr(solicitud, "estado", None) not in _ESTADOS_ABIERTOS:
        return 0
    total = 0
    total += _asegurar_legacy_ena(solicitud)
    for codigo in _PANELES_ASEGURAR:
        total += _asegurar_codigos_panel(solicitud, codigo)
    total += _asegurar_insumos_calculados(solicitud)
    return total
