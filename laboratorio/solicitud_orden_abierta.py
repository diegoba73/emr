"""Orden LIMS única abierta por paciente: merge de exámenes (y post-etiquetas si cabe en tubos)."""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.panel_componentes_orden import ordenar_queryset_panel

logger = logging.getLogger(__name__)

# Tubos activos: cierran el merge libre. Con solo PENDIENTE_TOMA se puede
# agregar si el examen cabe en tubos ya impresos (sin nueva extracción).
ESTADOS_MUESTRA_CIERRAN_ALTA = frozenset(
    {
        "PENDIENTE_TOMA",
        "TOMADA",
        "RECIBIDA",
        "EN_PROCESO",
        "CONSERVADA",
    }
)

# Órdenes del paciente que ya están en el circuito de lab (no PENDIENTE).
ESTADOS_ORDEN_EN_CURSO = frozenset(
    {
        "EN_PROCESO",
        "INFORMADO_PARCIAL",
        "LISTO_PARA_VALIDAR",
    }
)


class OrdenNoAbiertaError(ValueError):
    """No se pueden agregar exámenes: la orden ya no está abierta."""


class TuboNuevoRequeridoError(ValueError):
    """El examen no cabe en tubos impresos; requeriría una nueva extracción."""


def _iter_muestras(solicitud: SolicitudExamen):
    muestras = getattr(solicitud, "muestras", None)
    if muestras is None:
        return ()
    qs_or_list = muestras.all() if hasattr(muestras, "all") else muestras
    return qs_or_list


def orden_tiene_muestras_activas(solicitud: SolicitudExamen) -> bool:
    """True si hay tubos/etiquetas no terminales asociados a la orden."""
    for m in _iter_muestras(solicitud):
        estado = getattr(m, "estado", None)
        if estado in ESTADOS_MUESTRA_CIERRAN_ALTA:
            return True
    return False


def _muestras_activas_solo_pendiente_toma(solicitud: SolicitudExamen) -> bool:
    """True si hay tubos activos y todos están aún en PENDIENTE_TOMA."""
    activas = [
        m
        for m in _iter_muestras(solicitud)
        if getattr(m, "estado", None) in ESTADOS_MUESTRA_CIERRAN_ALTA
    ]
    if not activas:
        return False
    return all(getattr(m, "estado", None) == "PENDIENTE_TOMA" for m in activas)


def orden_esperando_recepcion(solicitud: SolicitudExamen) -> bool:
    """
    PENDIENTE con etiquetas impresas (tubos en PENDIENTE_TOMA):
    lista para recibir muestras. Se pueden agregar exámenes solo si caben
    en esos tubos (sin nueva extracción).
    """
    if getattr(solicitud, "estado", None) != "PENDIENTE":
        return False
    for m in _iter_muestras(solicitud):
        if getattr(m, "estado", None) == "PENDIENTE_TOMA":
            return True
    return False


def orden_permite_intentar_agregar_examenes(solicitud: SolicitudExamen) -> bool:
    """UI/API: se puede abrir el flujo de agregar (validación de tubos en el backend)."""
    if orden_esta_abierta(solicitud):
        return True
    return orden_esperando_recepcion(solicitud) and _muestras_activas_solo_pendiente_toma(
        solicitud
    )


def paciente_tiene_orden_en_curso(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> bool:
    """True si el paciente ya tiene otra orden EN_PROCESO / parcial / a validar."""
    qs = SolicitudExamen.objects.filter(
        paciente_id=paciente_id,
        estado__in=ESTADOS_ORDEN_EN_CURSO,
    )
    if exclude_solicitud_id is not None:
        qs = qs.exclude(pk=exclude_solicitud_id)
    return qs.exists()


def paciente_tiene_orden_bloqueada(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> bool:
    """
    True si el paciente ya tiene otra orden en curso de lab
    (EN_PROCESO / parcial / a validar) o PENDIENTE esperando recepción.
    """
    if paciente_tiene_orden_en_curso(
        paciente_id, exclude_solicitud_id=exclude_solicitud_id
    ):
        return True
    qs = (
        SolicitudExamen.objects.filter(paciente_id=paciente_id, estado="PENDIENTE")
        .prefetch_related("muestras")
        .order_by("-id")
    )
    if exclude_solicitud_id is not None:
        qs = qs.exclude(pk=exclude_solicitud_id)
    for sol in qs:
        if orden_esperando_recepcion(sol):
            return True
    return False


def orden_esta_abierta(solicitud: SolicitudExamen) -> bool:
    """PENDIENTE y sin etiquetas/tubos generados → admite agregar exámenes."""
    if getattr(solicitud, "estado", None) != "PENDIENTE":
        return False
    return not orden_tiene_muestras_activas(solicitud)


def buscar_orden_abierta(paciente_id: int) -> SolicitudExamen | None:
    """Última orden PENDIENTE del paciente aún editable (sin etiquetas)."""
    qs = (
        SolicitudExamen.objects.filter(paciente_id=paciente_id, estado="PENDIENTE")
        .prefetch_related("muestras")
        .order_by("-fecha_solicitud", "-id")
    )
    for sol in qs:
        if orden_esta_abierta(sol):
            return sol
    return None


def _resolver_tipo_examen_ids(
    examenes_ids: Iterable[int],
    paneles_ids: Iterable[int],
) -> tuple[set[int], set[int]]:
    """Devuelve (ids_analitos, ids_paneles_validos)."""
    exam_ids = {int(x) for x in (examenes_ids or []) if x is not None}
    panel_ids = {int(x) for x in (paneles_ids or []) if x is not None}
    tipos: set[int] = set()
    for tid in exam_ids:
        if TipoExamen.objects.filter(pk=tid).exists():
            tipos.add(tid)
        else:
            logger.warning("TipoExamen con ID %s no existe", tid)
    paneles_ok: set[int] = set()
    for pid in panel_ids:
        try:
            panel = PanelExamen.objects.get(pk=pid)
        except PanelExamen.DoesNotExist:
            logger.warning("PanelExamen con ID %s no existe", pid)
            continue
        paneles_ok.add(pid)
        for te in ordenar_queryset_panel(panel):
            tipos.add(te.id)
    return tipos, paneles_ok


def _assert_caben_en_tubos_impresos(
    sol: SolicitudExamen,
    tipos_ids: set[int],
    paneles_ids: set[int],
) -> None:
    """
    Dry-run: los nuevos tipos/paneles no deben exigir tubos adicionales
    respecto de las muestras ya impresas (PENDIENTE_TOMA).
    """
    from laboratorio.tubos_orden import TubosOrdenError, expandir_items_crear_muestras

    if not tipos_ids and not paneles_ids:
        return

    sin_tubo = list(
        TipoExamen.objects.filter(pk__in=tipos_ids)
        .filter(tipo_contenedor__isnull=True)
        .values_list("codigo", flat=True)[:8]
    )
    if sin_tubo:
        raise TuboNuevoRequeridoError(
            "No se pueden agregar exámenes sin tipo de tubo configurado "
            f"({', '.join(sin_tubo)}). Si requieren extracción nueva, creá un pedido adicional."
        )

    actuales_te = set(sol.tipos_examen.values_list("id", flat=True))
    actuales_p = set(sol.paneles.values_list("id", flat=True))
    agregar_te = sorted(tipos_ids - actuales_te)
    agregar_p = sorted(paneles_ids - actuales_p)
    if not agregar_te and not agregar_p:
        return

    try:
        if agregar_te:
            sol.tipos_examen.add(*agregar_te)
        if agregar_p:
            sol.paneles.add(*agregar_p)
        sol_fresh = (
            SolicitudExamen.objects.prefetch_related(
                "tipos_examen__tipo_contenedor",
                "tipos_examen__tipo_muestra_requerida",
                "paneles__tipos_examen__tipo_contenedor",
                "paneles__tipos_examen__tipo_muestra_requerida",
                "muestras",
            ).get(pk=sol.pk)
        )
        try:
            faltantes = expandir_items_crear_muestras(sol_fresh)
        except TubosOrdenError as exc:
            raise TuboNuevoRequeridoError(
                "No se pueden agregar estos exámenes a la orden con etiquetas ya impresas: "
                f"{exc}"
            ) from exc
        if faltantes:
            raise TuboNuevoRequeridoError(
                "Los exámenes seleccionados requieren un tubo o extracción nueva "
                "(tipo de muestra/contenedor distinto o capacidad del tubo excedida). "
                "Creá un pedido adicional para ese paciente."
            )
    finally:
        if agregar_te:
            sol.tipos_examen.remove(*agregar_te)
        if agregar_p:
            sol.paneles.remove(*agregar_p)


@transaction.atomic
def agregar_examenes_a_solicitud(
    solicitud: SolicitudExamen,
    examenes_ids: Iterable[int] | None = None,
    paneles_ids: Iterable[int] | None = None,
) -> SolicitudExamen:
    """
    Agrega paneles/exámenes faltantes a una orden.

    - Sin etiquetas (orden abierta): siempre permitido.
    - Con etiquetas (PENDIENTE_TOMA): solo si no hace falta un tubo nuevo.
    - Tras toma/recepción: rechazado.
    """
    sol = (
        SolicitudExamen.objects.select_for_update()
        .prefetch_related("muestras", "tipos_examen", "paneles", "resultados")
        .get(pk=solicitud.pk)
    )
    abierta = orden_esta_abierta(sol)
    post_etiquetas = (
        not abierta
        and orden_esperando_recepcion(sol)
        and _muestras_activas_solo_pendiente_toma(sol)
    )
    if not abierta and not post_etiquetas:
        raise OrdenNoAbiertaError(
            f"La orden {sol.numero or sol.pk} ya no admite exámenes "
            "(muestra en curso o estado distinto de pendiente). "
            "Creá una orden nueva para ese paciente."
        )

    tipos_nuevos, paneles_nuevos = _resolver_tipo_examen_ids(examenes_ids or [], paneles_ids or [])
    existentes = set(sol.resultados.values_list("tipo_examen_id", flat=True))

    if post_etiquetas:
        _assert_caben_en_tubos_impresos(sol, tipos_nuevos, paneles_nuevos)

    tipos_map = {
        t.id: t
        for t in TipoExamen.objects.filter(pk__in=tipos_nuevos - existentes).select_related(
            "laboratorio_derivacion"
        )
    }
    from laboratorio.derivacion_service import defaults_derivacion_para_tipo

    for tid in sorted(tipos_nuevos - existentes):
        te = tipos_map.get(tid)
        kwargs = defaults_derivacion_para_tipo(te) if te else {}
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen_id=tid,
            valor_obtenido="",
            es_patologico=False,
            **kwargs,
        )

    if tipos_nuevos:
        actuales_te = set(sol.tipos_examen.values_list("id", flat=True))
        sol.tipos_examen.set(actuales_te | tipos_nuevos)

    if paneles_nuevos:
        actuales_p = set(sol.paneles.values_list("id", flat=True))
        sol.paneles.set(actuales_p | paneles_nuevos)

    return (
        SolicitudExamen.objects.select_related(
            "paciente",
            "medico_interno",
            "consulta_hc__turno__recurso",
        )
        .prefetch_related(
            "tipos_examen",
            "paneles",
            "resultados__tipo_examen",
            "resultados__muestra",
            "muestras",
        )
        .get(pk=sol.pk)
    )
