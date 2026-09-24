"""
Carga de resultados de una SolicitudExamen (manual o instrumento).

Fuente única para ``POST .../cargar-resultados/`` y la ingesta de analizadores.
No valida ni informa: solo persiste borrador y sincroniza estado.
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot

from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import MuestraAccionError, aplicar_iniciar_proceso
from laboratorio.orden_grupos_informe import claves_grupos_validas, validar_orden_grupos
from laboratorio.qc_service import QcGateError, verificar_iqc_para_solicitud
from laboratorio.resultado_muestra_validacion import (
    asegurar_muestra_lista_para_carga,
    assert_muestra_estado_carga_resultado,
    assert_tipo_examen_muestra_carga,
)
from laboratorio.resultados_clinicos import aplicar_carga_estructurada
from laboratorio.solicitud_cierre import SolicitudCierreError, sincronizar_estado_tras_carga
from laboratorio.solicitud_estado import SolicitudEstadoTransitionError

logger = logging.getLogger(__name__)

ESTADOS_CARGABLES = frozenset({"EN_PROCESO", "INFORMADO_PARCIAL", "LISTO_PARA_VALIDAR"})


class CargaResultadosError(Exception):
    """Error de negocio al cargar resultados (mapeable a HTTP 400)."""

    def __init__(self, message: str, *, code: str = "carga_resultados"):
        super().__init__(message)
        self.code = code


def payload_item_tiene_valor(item: dict) -> bool:
    """True si el ítem trae un valor clínico para persistir (carga parcial)."""
    if str(item.get("valor_sysmex") or "").strip():
        return True
    valor = item.get("valor")
    if valor is None:
        valor = item.get("valor_obtenido")
    if valor is not None and str(valor).strip():
        return True
    vn = item.get("valor_numerico")
    return vn is not None and vn != ""


def _validation_message(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        first = next(iter(exc.message_dict.values()))
        return first[0] if isinstance(first, list) else str(first)
    if getattr(exc, "messages", None):
        return exc.messages[0]
    return str(exc)


def cargar_resultados_solicitud(
    *,
    solicitud_id: int,
    resultados_data: list[dict[str, Any]],
    actor,
    informar_parcial: bool = False,
    observaciones: str | None = None,
    observaciones_en_payload: bool = False,
    orden_grupos_informe: Any = None,
    orden_grupos_en_payload: bool = False,
    view: str = "SolicitudExamenViewSet.cargar_resultados",
    equipo_iqc=None,
    fuente: str = "MANUAL",
) -> SolicitudExamen:
    """
    Persiste valores en resultados de la orden y sincroniza estado.

    ``fuente``: MANUAL | INSTRUMENTO (solo metadata de auditoría).
    """
    if not resultados_data:
        raise CargaResultadosError("Se requiere una lista de resultados.")

    items_con_valor = [i for i in resultados_data if payload_item_tiene_valor(i)]
    if not items_con_valor:
        raise CargaResultadosError("Indique al menos un resultado con valor para guardar.")

    with transaction.atomic():
        solicitud = SolicitudExamen.objects.select_for_update().get(pk=solicitud_id)

        if solicitud.estado == "PENDIENTE":
            raise CargaResultadosError("Debe tomarse la muestra antes de cargar resultados.")
        if solicitud.estado == "FINALIZADO":
            raise CargaResultadosError(
                "La orden está validada y bloqueada. No se pueden modificar los resultados."
            )
        if solicitud.estado not in ESTADOS_CARGABLES:
            raise CargaResultadosError(
                "Solo se pueden cargar resultados en órdenes "
                "en proceso, informadas parcialmente o listas para validar."
            )

        try:
            verificar_iqc_para_solicitud(
                solicitud,
                actor=actor,
                permitir_override=False,
                equipo=equipo_iqc,
            )
        except QcGateError as exc:
            raise CargaResultadosError(str(exc), code="iqc") from exc

        before_solicitud = safe_model_snapshot(solicitud)

        if observaciones_en_payload:
            solicitud.observaciones = observaciones or ""
            solicitud.save(update_fields=["observaciones"])

        if orden_grupos_en_payload:
            claves = claves_grupos_validas(
                solicitud,
                solicitud.resultados.select_related("tipo_examen__tipo_muestra_requerida"),
            )
            orden_validado = validar_orden_grupos(orden_grupos_informe, claves)
            if orden_validado is None:
                raise CargaResultadosError(
                    "orden_grupos_informe debe ser una lista de claves válidas."
                )
            solicitud.orden_grupos_informe = orden_validado
            solicitud.save(update_fields=["orden_grupos_informe"])

        for resultado_item in items_con_valor:
            resultado_id = resultado_item.get("id")
            if not resultado_id:
                continue

            try:
                resultado = ResultadoExamen.objects.select_for_update(of=("self",)).get(
                    id=resultado_id,
                    solicitud=solicitud,
                )
            except ResultadoExamen.DoesNotExist:
                logger.warning("ResultadoExamen inexistente para carga de resultados")
                continue

            before_res = safe_model_snapshot(resultado)
            prev_muestra_id = resultado.muestra_id
            muestra_meta_aplica = False
            muestra_iniciar_proceso_id: int | None = None
            era_vacio = not (resultado.valor_obtenido or "").strip()

            if "muestra_id" in resultado_item:
                if resultado.validado_por_id or resultado.fecha_validacion:
                    raise CargaResultadosError(
                        "No se puede cambiar la muestra de un resultado validado."
                    )
                muestra_meta_aplica = True
                raw_muestra_id = resultado_item.get("muestra_id")
                if raw_muestra_id is None:
                    resultado.muestra = None
                else:
                    try:
                        muestra = Muestra.objects.select_for_update().get(
                            pk=raw_muestra_id,
                            solicitud_id=solicitud.pk,
                        )
                    except Muestra.DoesNotExist as exc:
                        raise CargaResultadosError(
                            "La muestra no existe o no pertenece a esta solicitud."
                        ) from exc
                    if muestra.paciente_id != solicitud.paciente_id:
                        raise CargaResultadosError(
                            "La muestra no corresponde al paciente de la solicitud."
                        )
                    try:
                        asegurar_muestra_lista_para_carga(
                            muestra,
                            actor=actor,
                            view=view,
                        )
                        assert_muestra_estado_carga_resultado(muestra)
                    except ValueError as exc:
                        raise CargaResultadosError(str(exc)) from exc
                    resultado.muestra = muestra
                    if muestra.estado in ("RECIBIDA", "CONSERVADA"):
                        muestra_iniciar_proceso_id = muestra.pk

            try:
                assert_tipo_examen_muestra_carga(
                    tipo_examen=resultado.tipo_examen,
                    resultado_muestra=resultado.muestra,
                    muestra_id_en_payload="muestra_id" in resultado_item,
                    raw_muestra_id=resultado_item.get("muestra_id"),
                )
            except ValueError as exc:
                raise CargaResultadosError(str(exc)) from exc

            try:
                audit_estructurado = aplicar_carga_estructurada(
                    resultado,
                    resultado.tipo_examen,
                    resultado_item,
                )
                audit_estructurado["valor_presente"] = bool(
                    (resultado.valor_obtenido or "").strip()
                )
            except ValidationError as exc:
                raise CargaResultadosError(_validation_message(exc)) from exc

            if (resultado.valor_obtenido or "").strip() and resultado.estado_derivacion in (
                "PENDIENTE_ENVIO",
                "ENVIADO",
            ):
                resultado.estado_derivacion = "RESULTADO_RECIBIDO"
            try:
                resultado.save()
            except ValidationError as exc:
                raise CargaResultadosError(_validation_message(exc)) from exc

            if era_vacio and (resultado.valor_obtenido or "").strip():
                try:
                    from laboratorio.inventario_service import egresar_por_resultado

                    inv = egresar_por_resultado(resultado, user=actor)
                    for w in inv.get("warnings") or []:
                        logger.warning("inventario (carga resultado %s): %s", resultado.pk, w)
                except Exception:
                    logger.exception(
                        "inventario: fallo egreso por resultado %s",
                        resultado.pk,
                    )

            muestra_transitioned_en_proceso = False
            muestra_estado_antes_proceso: str | None = None
            if muestra_iniciar_proceso_id is not None:
                muestra_estado_antes_proceso = (
                    Muestra.objects.filter(pk=muestra_iniciar_proceso_id)
                    .values_list("estado", flat=True)
                    .first()
                )
                try:
                    aplicar_iniciar_proceso(
                        muestra_iniciar_proceso_id,
                        actor=actor,
                        view=view,
                        resultado_id=resultado.pk,
                    )
                    muestra_transitioned_en_proceso = True
                except MuestraAccionError:
                    pass
            meta_carga = {
                "action": "cargar_resultados",
                "accion": "cargar_resultados",
                "view": view,
                "fuente": fuente,
                "resultado_id": resultado.pk,
                "solicitud_id": solicitud.pk,
                "numero_solicitud": solicitud.numero,
                "actor_id": getattr(actor, "pk", None),
                **audit_estructurado,
            }
            if muestra_transitioned_en_proceso and muestra_estado_antes_proceso:
                meta_carga["muestra_estado_anterior"] = muestra_estado_antes_proceso
                meta_carga["muestra_estado_nuevo"] = "EN_PROCESO"
            if muestra_meta_aplica:
                meta_carga["muestra_id"] = resultado.muestra_id
            if prev_muestra_id != resultado.muestra_id and muestra_meta_aplica:
                meta_carga["accion"] = "resultado_muestra_asociar"
                meta_carga["muestra_anterior_id"] = prev_muestra_id
                meta_carga["muestra_nueva_id"] = resultado.muestra_id
            log_update(
                actor=actor,
                entity=resultado,
                before=before_res,
                module="laboratorio",
                metadata=meta_carga,
            )

        solicitud.refresh_from_db()
        from laboratorio.calculos_derivados import aplicar_calculos_derivados_solicitud
        from laboratorio.hemograma_resultados import asegurar_resultados_paneles_derivados

        asegurar_resultados_paneles_derivados(solicitud)
        aplicar_calculos_derivados_solicitud(solicitud, solo_calculados=True, actor=actor, view=view)

        try:
            sincronizar_estado_tras_carga(
                solicitud,
                actor=actor,
                view=view,
                informar_parcial=informar_parcial,
            )
        except SolicitudCierreError:
            raise

        solicitud.refresh_from_db()
        log_update(
            actor=actor,
            entity=solicitud,
            before=before_solicitud,
            module="laboratorio",
            metadata={
                "action": "cargar_resultados",
                "accion": "cargar_resultados",
                "view": view,
                "fuente": fuente,
                "estado_anterior": before_solicitud.get("estado"),
                "estado_nuevo": solicitud.estado,
                "solicitud_id": solicitud.pk,
                "numero_solicitud": solicitud.numero,
            },
        )
        logger.debug("cargar_resultados completado solicitud_id=%s", solicitud.pk)
        return solicitud


__all__ = [
    "CargaResultadosError",
    "ESTADOS_CARGABLES",
    "cargar_resultados_solicitud",
    "payload_item_tiene_valor",
]
