"""Orden LIMS única abierta por paciente: merge de exámenes (y post-etiquetas / en curso).

Si el examen cabe en tubos existentes se reutilizan; si requiere otro contenedor
o supera capacidad, se crean tubos nuevos en PENDIENTE_TOMA para extracción.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.panel_componentes_orden import ordenar_queryset_panel

logger = logging.getLogger(__name__)

# Tubos activos: cierran el merge libre (alta vía create). Agregar a orden
# con tubos sigue permitido: mismo tubo o tubo/extracción nueva.
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
    """No se pudo resolver el tubo del examen (p. ej. sin tipo_contenedor)."""


class QuitarExamenError(ValueError):
    """No se pueden quitar exámenes o paneles de la orden."""


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
    lista para recibir muestras. Se pueden agregar exámenes; si hace falta
    otro tubo se genera en PENDIENTE_TOMA.
    """
    if getattr(solicitud, "estado", None) != "PENDIENTE":
        return False
    for m in _iter_muestras(solicitud):
        if getattr(m, "estado", None) == "PENDIENTE_TOMA":
            return True
    return False


def orden_en_curso(solicitud: SolicitudExamen) -> bool:
    """True si la orden está en el circuito de lab (no PENDIENTE ni FINALIZADO)."""
    return getattr(solicitud, "estado", None) in ESTADOS_ORDEN_EN_CURSO


def orden_permite_intentar_agregar_examenes(solicitud: SolicitudExamen) -> bool:
    """UI/API: se puede abrir el flujo de agregar (validación de tubos en el backend)."""
    if orden_esta_abierta(solicitud):
        return True
    if orden_esperando_recepcion(solicitud) and _muestras_activas_solo_pendiente_toma(
        solicitud
    ):
        return True
    return orden_en_curso(solicitud)


def orden_permite_quitar_examenes(solicitud: SolicitudExamen) -> bool:
    """PENDIENTE o en curso: se puede intentar quitar (el backend valida resultados)."""
    estado = getattr(solicitud, "estado", None)
    if estado == "FINALIZADO":
        return False
    return estado == "PENDIENTE" or estado in ESTADOS_ORDEN_EN_CURSO


MENSAJE_LAB_INTERNACION_SIN_FINALIZAR = (
    'No se puede solicitar un nuevo análisis: el paciente ya tiene un análisis '
    'de internación en proceso (no finalizado). Esperá a que el laboratorio lo complete.'
)


def paciente_tiene_analisis_internacion_sin_finalizar(
    paciente_id: int, *, fecha_programada_toma=None
) -> bool:
    """
    True si hay orden de internación no finalizada que colisiona con el día
    de extracción indicado. Sin fecha: cualquier orden no finalizada (legado).
    Con fecha: solo las del mismo día (permite programar mañana con otra
    orden de hoy aún abierta o en proceso).
    """
    from laboratorio.origen_solicitud import INTERNACION_UCE, INTERNACION_UCO

    qs = SolicitudExamen.objects.filter(
        paciente_id=paciente_id,
        origen_solicitud__in=(INTERNACION_UCO, INTERNACION_UCE),
    ).exclude(estado="FINALIZADO")
    if fecha_programada_toma is not None:
        qs = qs.filter(fecha_programada_toma=fecha_programada_toma)
    return qs.exists()


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


def buscar_orden_abierta(
    paciente_id: int, *, fecha_programada_toma=None
) -> SolicitudExamen | None:
    """Última orden PENDIENTE del paciente aún editable (sin etiquetas).

    Si ``fecha_programada_toma`` se indica, solo considera órdenes de ese día
    de extracción (hoy y mañana no se fusionan entre sí).
    """
    qs = (
        SolicitudExamen.objects.filter(paciente_id=paciente_id, estado="PENDIENTE")
        .prefetch_related("muestras")
        .order_by("-fecha_solicitud", "-id")
    )
    if fecha_programada_toma is not None:
        qs = qs.filter(fecha_programada_toma=fecha_programada_toma)
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


def _assert_examenes_con_tubo_configurado(tipos_ids: set[int]) -> None:
    """Rechaza exámenes sin tipo_contenedor (no se puede generar tubo)."""
    if not tipos_ids:
        return
    sin_tubo = list(
        TipoExamen.objects.filter(pk__in=tipos_ids)
        .filter(tipo_contenedor__isnull=True)
        .values_list("codigo", flat=True)[:8]
    )
    if sin_tubo:
        raise TuboNuevoRequeridoError(
            "No se pueden agregar exámenes sin tipo de tubo configurado "
            f"({', '.join(sin_tubo)})."
        )


def _crear_tubos_faltantes_tras_agregar(
    sol: SolicitudExamen,
    *,
    user=None,
) -> int:
    """
    Tras sumar tipos/paneles: crea Muestra PENDIENTE_TOMA por cada tubo faltante
    (otro contenedor/muestra o capacidad excedida). Devuelve cantidad creada.
    """
    from laboratorio.muestra_estado import crear_muestra
    from laboratorio.tubos_orden import TubosOrdenError, expandir_items_crear_muestras

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
            f"No se pueden generar los tubos para los exámenes agregados: {exc}"
        ) from exc

    creados = 0
    for item in faltantes:
        crear_muestra(
            solicitud=sol_fresh,
            tipo_muestra_id=int(item["tipo_muestra_id"]),
            tipo_contenedor_id=item.get("tipo_contenedor_id"),
            observaciones=item.get("observaciones") or "Tubo por examen agregado a la orden",
            actor=user,
            view="agregar_examenes",
        )
        creados += 1
    return creados


@transaction.atomic
def agregar_examenes_a_solicitud(
    solicitud: SolicitudExamen,
    examenes_ids: Iterable[int] | None = None,
    paneles_ids: Iterable[int] | None = None,
    *,
    user=None,
) -> SolicitudExamen:
    """
    Agrega paneles/exámenes faltantes a una orden.

    - Sin etiquetas (orden abierta): siempre permitido (tubos al imprimir).
    - Con etiquetas o en curso: reutiliza tubos existentes; si hace falta otro
      tubo/extracción, crea Muestra en PENDIENTE_TOMA.
    - FINALIZADO: rechazado.
    - Frecuencia PROBNP: ver restricciones_frecuencia (salvo lab/bioquímico).
    """
    from laboratorio.restricciones_frecuencia import assert_puede_agregar_probnp

    sol = (
        SolicitudExamen.objects.select_for_update()
        .prefetch_related("muestras", "tipos_examen", "paneles", "resultados")
        .get(pk=solicitud.pk)
    )
    if not orden_permite_intentar_agregar_examenes(sol):
        raise OrdenNoAbiertaError(
            f"La orden {sol.numero or sol.pk} no admite agregar exámenes "
            "(finalizada o estado no editable). "
            "Creá una orden nueva para ese paciente."
        )

    tipos_nuevos, paneles_nuevos = _resolver_tipo_examen_ids(examenes_ids or [], paneles_ids or [])
    assert_puede_agregar_probnp(
        user,
        sol.paciente_id,
        tipos_nuevos,
        exclude_solicitud_id=sol.pk,
    )
    existentes = set(sol.resultados.values_list("tipo_examen_id", flat=True))

    # Con tubos ya generados, los nuevos ítems deben poder resolverse a contenedor.
    if not orden_esta_abierta(sol) and orden_tiene_muestras_activas(sol):
        _assert_examenes_con_tubo_configurado(tipos_nuevos)

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

    if not orden_esta_abierta(sol) and orden_tiene_muestras_activas(sol):
        _crear_tubos_faltantes_tras_agregar(sol, user=user)

    if orden_en_curso(sol):
        _sincronizar_estado_tras_cambio_items(sol, view="agregar_examenes")

    return _solicitud_refrescada(sol.pk)


def _solicitud_refrescada(pk: int) -> SolicitudExamen:
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
        .get(pk=pk)
    )


def _sincronizar_estado_tras_cambio_items(sol: SolicitudExamen, *, view: str) -> None:
    """Si se agregan vacíos o se quitan ítems, reabre / cierra carga según corresponda."""
    from laboratorio.solicitud_cierre import SolicitudCierreError, sincronizar_estado_tras_carga
    from laboratorio.solicitud_estado import SolicitudEstadoTransitionError

    try:
        sincronizar_estado_tras_carga(sol, actor=None, view=view)
    except (SolicitudCierreError, SolicitudEstadoTransitionError) as exc:
        logger.warning("No se pudo sincronizar estado tras %s: %s", view, exc)


def _ids_tipos_de_paneles(panel_ids: set[int]) -> set[int]:
    if not panel_ids:
        return set()
    ids: set[int] = set()
    for panel in PanelExamen.objects.filter(pk__in=panel_ids).prefetch_related("tipos_examen"):
        ids.update(panel.tipos_examen.values_list("id", flat=True))
    return ids


def _resultado_es_vacio(res: ResultadoExamen) -> bool:
    if (res.valor_obtenido or "").strip():
        return False
    if res.valor_numerico is not None:
        return False
    if res.validado_por_id or res.fecha_validacion:
        return False
    return True


def _podar_orden_grupos_informe(sol: SolicitudExamen) -> None:
    orden_custom = list(sol.orden_grupos_informe or [])
    if not orden_custom:
        return
    from laboratorio.orden_grupos_informe import claves_grupos_validas

    remaining = list(
        ResultadoExamen.objects.filter(solicitud=sol).select_related("tipo_examen")
    )
    valid = claves_grupos_validas(sol, remaining)
    pruned = [k for k in orden_custom if k in valid]
    if pruned != orden_custom:
        sol.orden_grupos_informe = pruned
        sol.save(update_fields=["orden_grupos_informe"])


@transaction.atomic
def quitar_examenes_de_solicitud(
    solicitud: SolicitudExamen,
    examenes_ids: Iterable[int] | None = None,
    paneles_ids: Iterable[int] | None = None,
) -> SolicitudExamen:
    """
    Quita paneles/exámenes de una orden PENDIENTE o en curso.

    - FINALIZADO: rechazado.
    - Resultado con valor o validado: rechazado (toda la operación).
    - Al quitar un panel, se quitan los componentes que no sigan cubiertos
      por otro panel restante.
    - Un examen pedido explícitamente no se quita si sigue cubierto por un
      panel que permanece en la orden.
    """
    sol = (
        SolicitudExamen.objects.select_for_update()
        .prefetch_related("muestras", "tipos_examen", "paneles", "resultados__tipo_examen")
        .get(pk=solicitud.pk)
    )
    if not orden_permite_quitar_examenes(sol):
        raise QuitarExamenError(
            f"La orden {sol.numero or sol.pk} no admite quitar exámenes "
            "(finalizada o estado no editable)."
        )

    exam_ids = {int(x) for x in (examenes_ids or []) if x is not None}
    panel_ids_req = {int(x) for x in (paneles_ids or []) if x is not None}

    paneles_actuales = set(sol.paneles.values_list("id", flat=True))
    tipos_actuales = set(sol.tipos_examen.values_list("id", flat=True))
    tipos_en_resultados = set(sol.resultados.values_list("tipo_examen_id", flat=True))

    paneles_quitar = panel_ids_req & paneles_actuales
    examenes_explicitos = exam_ids & (tipos_actuales | tipos_en_resultados)

    if not paneles_quitar and not examenes_explicitos:
        raise QuitarExamenError(
            "Ninguno de los exámenes o paneles indicados está en la orden."
        )

    paneles_restantes = paneles_actuales - paneles_quitar
    cubiertos_restantes = _ids_tipos_de_paneles(paneles_restantes)

    conflictos = sorted(examenes_explicitos & cubiertos_restantes)
    if conflictos:
        nombres = list(
            TipoExamen.objects.filter(pk__in=conflictos).values_list("nombre", flat=True)[:8]
        )
        raise QuitarExamenError(
            "No se puede quitar un examen que sigue formando parte de un panel "
            "de la orden. Quitá el panel o dejá el examen"
            + (f" ({', '.join(nombres)})." if nombres else ".")
        )

    tipos_por_panel = _ids_tipos_de_paneles(paneles_quitar) - cubiertos_restantes
    tipos_a_quitar = examenes_explicitos | tipos_por_panel

    bloqueados: list[str] = []
    a_borrar: list[int] = []
    for res in sol.resultados.filter(tipo_examen_id__in=tipos_a_quitar).select_related(
        "tipo_examen"
    ):
        nombre = res.tipo_examen.nombre if res.tipo_examen_id else str(res.pk)
        if not _resultado_es_vacio(res):
            if res.validado_por_id or res.fecha_validacion:
                bloqueados.append(f"{nombre} (validado)")
            else:
                bloqueados.append(f"{nombre} (con resultado)")
        else:
            a_borrar.append(res.pk)

    if bloqueados:
        raise QuitarExamenError(
            "No se pueden quitar exámenes con resultado cargado o validados: "
            + ", ".join(bloqueados)
        )

    if paneles_quitar:
        sol.paneles.remove(*paneles_quitar)
    if tipos_a_quitar:
        sol.tipos_examen.remove(*tipos_a_quitar)
    if a_borrar:
        ResultadoExamen.objects.filter(pk__in=a_borrar).delete()

    _podar_orden_grupos_informe(sol)

    if orden_en_curso(sol):
        _sincronizar_estado_tras_cambio_items(sol, view="quitar_examenes")

    return _solicitud_refrescada(sol.pk)
