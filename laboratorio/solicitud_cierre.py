"""
Cierre y estados de SolicitudExamen al completar resultados / validar / informar parcial.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from django.utils import timezone

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import MuestraAccionError, aplicar_iniciar_proceso
from laboratorio.resultado_muestra_validacion import (
    MUESTRA_ESTADOS_PENDIENTES_RECEPCION,
    MUESTRA_ESTADOS_TERMINALES_SIN_RESULTADO,
    asegurar_muestra_lista_para_carga,
)
from laboratorio.solicitud_estado import (
    ESTADOS_SOLICITUD_EDITABLES,
    SolicitudEstadoTransitionError,
    apply_solicitud_estado_transition,
)
from laboratorio.tubos_orden import mapa_tipo_examen_a_clave_tubo

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class SolicitudCierreError(ValueError):
    """No se puede cerrar la solicitud (resultados incompletos o muestras inválidas)."""


def _resultado_tiene_valor(resultado: ResultadoExamen) -> bool:
    return bool((resultado.valor_obtenido or "").strip())


def _claves_tubo_solo_terminales(solicitud: SolicitudExamen) -> set[tuple[int | None, int | None]]:
    """
    Claves (contenedor, tipo_muestra) de la orden que solo tienen tubos
    CANCELADA / RECHAZADA / DESCARTADA (ninguno activo).
    """
    por_clave: dict[tuple[int | None, int | None], list[str]] = defaultdict(list)
    for tc_id, tm_id, estado in Muestra.objects.filter(solicitud_id=solicitud.pk).values_list(
        "tipo_contenedor_id", "tipo_muestra_id", "estado"
    ):
        por_clave[(tc_id, tm_id)].append(estado)

    solo_terminales: set[tuple[int | None, int | None]] = set()
    for clave, estados in por_clave.items():
        if not estados:
            continue
        if all(e in MUESTRA_ESTADOS_TERMINALES_SIN_RESULTADO for e in estados):
            solo_terminales.add(clave)
    return solo_terminales


def _resultado_exigible_para_cierre(
    resultado: ResultadoExamen,
    *,
    mapa_tubo: dict[int, tuple[int | None, int | None]],
    claves_solo_terminales: set[tuple[int | None, int | None]],
    muestra_por_id: dict[int, Muestra],
) -> bool:
    """
    True si el resultado cuenta para completitud / validar.

    - Con valor: siempre exigible.
    - Vacío vinculado a tubo terminal: no exigible.
    - Vacío cuyo contenedor requerido solo tiene tubos terminales: no exigible.
    - Resto de vacíos: exigibles.
    """
    if _resultado_tiene_valor(resultado):
        return True

    if resultado.muestra_id:
        m = muestra_por_id.get(resultado.muestra_id)
        if m is not None and m.estado in MUESTRA_ESTADOS_TERMINALES_SIN_RESULTADO:
            return False

    clave = mapa_tubo.get(resultado.tipo_examen_id)
    if clave is not None and clave in claves_solo_terminales:
        return False
    return True


def _resultados_exigibles_cierre(solicitud: SolicitudExamen) -> list[ResultadoExamen]:
    resultados = list(solicitud.resultados.select_related("muestra", "tipo_examen").all())
    if not resultados:
        return []
    mapa_tubo = mapa_tipo_examen_a_clave_tubo(solicitud)
    claves_solo_terminales = _claves_tubo_solo_terminales(solicitud)
    muestra_por_id = {
        r.muestra_id: r.muestra
        for r in resultados
        if r.muestra_id and getattr(r, "muestra", None) is not None
    }
    # Completar muestras no prefetchadas por FK directa
    faltantes = {
        r.muestra_id
        for r in resultados
        if r.muestra_id and r.muestra_id not in muestra_por_id
    }
    if faltantes:
        for m in Muestra.objects.filter(pk__in=faltantes):
            muestra_por_id[m.pk] = m

    return [
        r
        for r in resultados
        if _resultado_exigible_para_cierre(
            r,
            mapa_tubo=mapa_tubo,
            claves_solo_terminales=claves_solo_terminales,
            muestra_por_id=muestra_por_id,
        )
    ]


def solicitud_resultados_completos(solicitud: SolicitudExamen) -> bool:
    """
    True si todo resultado *exigible* tiene valor.

    Los vacíos asociados a tubos cancelados/rechazados/descartados (o cuyo
    contenedor solo tiene esos tubos) no bloquean el cierre.
    """
    exigibles = _resultados_exigibles_cierre(solicitud)
    if not exigibles:
        return False
    return all(_resultado_tiene_valor(r) for r in exigibles)


def _preparar_muestras_para_cierre(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
) -> None:
    """
    Recepciona tubos TOMADA y los deja EN_PROCESO antes de validar el cierre.
    Evita fallos al finalizar cuando la muestra ya estaba vinculada al resultado.
    """
    muestra_ids = list(
        solicitud.resultados.exclude(valor_obtenido="")
        .filter(muestra_id__isnull=False)
        .values_list("muestra_id", flat=True)
        .distinct()
    )
    if not muestra_ids:
        return
    for m in Muestra.objects.select_for_update().filter(pk__in=muestra_ids):
        asegurar_muestra_lista_para_carga(m, actor=actor, view=view)
        m.refresh_from_db()
        if m.estado in ("RECIBIDA", "CONSERVADA"):
            try:
                aplicar_iniciar_proceso(m.pk, actor=actor, view=view)
            except MuestraAccionError:
                pass


def orden_tiene_tubos_pendientes_recepcion(solicitud: SolicitudExamen) -> bool:
    """True si quedan tubos PENDIENTE_TOMA o TOMADA (aún no recepcionados)."""
    return Muestra.objects.filter(
        solicitud_id=solicitud.pk,
        estado__in=MUESTRA_ESTADOS_PENDIENTES_RECEPCION,
    ).exists()


MSG_TUBOS_PENDIENTES_RECEPCION = (
    "Hay tubos pendientes de recepción. Recibilos o cancelalos (o rechazadlos) "
    "antes de marcar la orden como lista para validar."
)


def _assert_sin_tubos_pendientes_recepcion(solicitud: SolicitudExamen) -> None:
    if orden_tiene_tubos_pendientes_recepcion(solicitud):
        raise SolicitudCierreError(MSG_TUBOS_PENDIENTES_RECEPCION)


def _validar_muestras_para_cierre(solicitud: SolicitudExamen) -> None:
    """
    Reglas al validar:
    1) No puede haber tubos aún PENDIENTE_TOMA/TOMADA en la orden.
    2) Resultados *con valor* no pueden apuntar a muestra pendiente/tomada
       ni terminal (CANCELADA/RECHAZADA/DESCARTADA). Los vacíos sobre tubos
       cancelados no bloquean (no son exigibles).
    """
    _assert_sin_tubos_pendientes_recepcion(solicitud)
    muestra_ids = list(
        solicitud.resultados.exclude(valor_obtenido="")
        .filter(muestra_id__isnull=False)
        .values_list("muestra_id", flat=True)
        .distinct()
    )
    if not muestra_ids:
        return
    # Pendiente/tomada o terminal: no validar valores atados a esos tubos.
    estados_invalidos_con_valor = (
        MUESTRA_ESTADOS_PENDIENTES_RECEPCION | MUESTRA_ESTADOS_TERMINALES_SIN_RESULTADO
    )
    for m in Muestra.objects.filter(pk__in=muestra_ids):
        if m.estado in estados_invalidos_con_valor:
            raise SolicitudCierreError(
                "Hay un resultado vinculado a una muestra en estado incompatible."
            )


def solicitud_tiene_algun_resultado(solicitud: SolicitudExamen) -> bool:
    return solicitud.resultados.exclude(valor_obtenido="").exists()


def solicitud_resultados_parciales(solicitud: SolicitudExamen) -> bool:
    return solicitud_tiene_algun_resultado(solicitud) and not solicitud_resultados_completos(solicitud)


def informar_parcial_si_corresponde(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
) -> bool:
    """
    Marca la orden como INFORMADO_PARCIAL si hay al menos un resultado cargado
    y aún faltan valores. No finaliza. Devuelve True si el estado es (o queda) parcial.
    """
    if solicitud.estado == "FINALIZADO":
        return False
    if solicitud.estado == "LISTO_PARA_VALIDAR":
        return False
    if not solicitud_resultados_parciales(solicitud):
        return False
    if solicitud.estado == "INFORMADO_PARCIAL":
        return True
    if solicitud.estado != "EN_PROCESO":
        return False
    apply_solicitud_estado_transition(
        solicitud,
        "INFORMADO_PARCIAL",
        actor=actor,
        accion="informar_parcial",
        view=view,
    )
    return True


def sincronizar_estado_tras_carga(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    informar_parcial: bool = False,
) -> str:
    """
    Tras cargar resultados:
    - Completos y sin tubos pendientes de recepción → LISTO_PARA_VALIDAR
      (desde EN_PROCESO o INFORMADO_PARCIAL).
    - Completos pero con tubos PENDIENTE_TOMA/TOMADA → no promover a listo
      (hay que recepcionar o cancelar esos tubos; se puede seguir cargando
      resultados de tubos ya recibidos).
    - Incompletos + informar_parcial → INFORMADO_PARCIAL.
    - Incompletos desde LISTO_PARA_VALIDAR → EN_PROCESO (reabrir).
    """
    solicitud.refresh_from_db()
    if solicitud.estado == "FINALIZADO":
        return solicitud.estado

    completos = solicitud_resultados_completos(solicitud)
    tubos_pendientes = orden_tiene_tubos_pendientes_recepcion(solicitud)

    if completos and not tubos_pendientes:
        if solicitud.estado in ("EN_PROCESO", "INFORMADO_PARCIAL"):
            apply_solicitud_estado_transition(
                solicitud,
                "LISTO_PARA_VALIDAR",
                actor=actor,
                accion="completar_carga",
                view=view,
            )
        return solicitud.estado

    # Incompletos, o completos pero con tubos aún no recepcionados
    if solicitud.estado == "LISTO_PARA_VALIDAR":
        apply_solicitud_estado_transition(
            solicitud,
            "EN_PROCESO",
            actor=actor,
            accion="reabrir_carga",
            view=view,
        )
        return solicitud.estado

    if informar_parcial:
        if not solicitud_tiene_algun_resultado(solicitud):
            raise SolicitudCierreError(
                "No hay resultados cargados para informar parcialmente."
            )
        informar_parcial_si_corresponde(solicitud, actor=actor, view=view)

    return solicitud.estado


def finalizar_solicitud_si_completa(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    accion: str = "validar",
    confirmar_criticos: bool = False,
) -> bool:
    """
    Pasa LISTO_PARA_VALIDAR → FINALIZADO si todos los resultados tienen valor.
    Devuelve True si se aplicó la transición.

    Requiere confirmación explícita si hay resultados fuera de rango o críticos.
    """
    if solicitud.estado != "LISTO_PARA_VALIDAR":
        return False
    if not solicitud_resultados_completos(solicitud):
        return False
    _preparar_muestras_para_cierre(solicitud, actor=actor, view=view)
    _validar_muestras_para_cierre(solicitud)

    qs = solicitud.resultados.all()
    tiene_alertas = qs.filter(es_patologico=True).exists() or qs.filter(es_critico=True).exists()
    if tiene_alertas and not confirmar_criticos:
        raise SolicitudCierreError(
            "Hay resultados fuera de rango o críticos. Confirme la liberación "
            "enviando confirmar_criticos=true."
        )

    before_resultados = {r.id: safe_model_snapshot(r) for r in qs}

    apply_solicitud_estado_transition(
        solicitud,
        "FINALIZADO",
        actor=actor,
        accion=accion,
        view=view,
    )

    now = timezone.now()
    solicitud.resultados.update(
        validado_por=actor,
        fecha_validacion=now,
    )
    solicitud.refresh_from_db()

    for res in ResultadoExamen.objects.filter(solicitud_id=solicitud.pk):
        log_update(
            actor=actor,
            entity=res,
            before=before_resultados[res.id],
            module="laboratorio",
            metadata={
                "action": accion,
                "accion": accion,
                "view": view,
            },
        )
    return True


def finalizar_solicitud_manual(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    confirmar_criticos: bool = False,
    confirmar_qc_override: bool = False,
    motivo_qc_override: str = "",
) -> None:
    """Cierre explícito (validación / liberación clínica) desde LISTO_PARA_VALIDAR."""
    if solicitud.estado == "FINALIZADO":
        raise SolicitudEstadoTransitionError("La solicitud ya está finalizada.")
    if solicitud.estado != "LISTO_PARA_VALIDAR":
        raise SolicitudEstadoTransitionError(
            "Solo se pueden validar órdenes en estado «Listo para validar» "
            "(todos los resultados deben estar cargados)."
        )
    if not solicitud_resultados_completos(solicitud):
        raise SolicitudCierreError(
            "No se puede finalizar una solicitud con resultados vacíos."
        )

    from laboratorio.obra_social import MENSAJE_NO_AUTORIZADA, obra_social_permite_liberar

    if not obra_social_permite_liberar(solicitud):
        raise SolicitudCierreError(MENSAJE_NO_AUTORIZADA)

    from laboratorio.qc_service import validar_qc_para_cierre

    validar_qc_para_cierre(
        solicitud,
        confirmar_qc_override=confirmar_qc_override,
        motivo_override=motivo_qc_override,
        actor=actor,
    )

    if not finalizar_solicitud_si_completa(
        solicitud,
        actor=actor,
        view=view,
        accion="validar",
        confirmar_criticos=confirmar_criticos,
    ):
        raise SolicitudCierreError("No se pudo finalizar la solicitud.")


def desvalidar_solicitud_manual(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    motivo: str = "",
) -> None:
    """
    Reabre una orden FINALIZADO → LISTO_PARA_VALIDAR para corregir resultados
    y volver a validar. Limpia sellos de validación en cada ResultadoExamen.
    """
    motivo_limpio = (motivo or "").strip()
    if len(motivo_limpio) < 5:
        raise SolicitudCierreError(
            "Indicá un motivo de la reapertura (mínimo 5 caracteres)."
        )
    if solicitud.estado != "FINALIZADO":
        raise SolicitudEstadoTransitionError(
            "Solo se pueden reabrir para corrección órdenes ya validadas (FINALIZADO)."
        )

    qs = list(solicitud.resultados.all())
    before_resultados = {r.id: safe_model_snapshot(r) for r in qs}

    apply_solicitud_estado_transition(
        solicitud,
        "LISTO_PARA_VALIDAR",
        actor=actor,
        accion="desvalidar",
        view=view,
        extra_metadata={"motivo": motivo_limpio[:500]},
    )

    ResultadoExamen.objects.filter(solicitud_id=solicitud.pk).update(
        validado_por=None,
        fecha_validacion=None,
    )
    solicitud.refresh_from_db()

    for res in ResultadoExamen.objects.filter(solicitud_id=solicitud.pk):
        log_update(
            actor=actor,
            entity=res,
            before=before_resultados.get(res.id),
            module="laboratorio",
            metadata={
                "action": "desvalidar",
                "accion": "desvalidar",
                "view": view,
                "motivo": motivo_limpio[:200],
            },
        )


def solicitud_permite_cargar_resultados(solicitud: SolicitudExamen) -> bool:
    return solicitud.estado in ESTADOS_SOLICITUD_EDITABLES
