"""
Transiciones de estado controladas para EstudioMicrobiologia y servicios de
creación auditados de SiembraMicrobiologia / LecturaCultivo (LIMS Fase B3.1).

Reglas:

- El estado del estudio NO se modifica por PATCH/PUT directo (campo read-only
  en el serializer); las transiciones ocurren sólo aquí.
- Patrón de auditoría idéntico a ``muestra_estado``: ``transaction.atomic`` +
  ``select_for_update`` + ``safe_model_snapshot`` + ``log_create``/``log_update``
  con ``transaction.on_commit``.
- B3.1 no incluye microorganismos, aislados, antibiograma ni informes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.utils import timezone

from auditoria.audit_service import log_create, log_update
from auditoria.context import get_request_id
from auditoria.snapshot import safe_model_snapshot

from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    MedioCultivo,
    Microorganismo,
    MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class MicrobiologiaAccionError(ValueError):
    """Acción o transición no permitida sobre el estudio/siembra/lectura."""


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def _base_estudio_metadata(
    estudio: EstudioMicrobiologia,
    *,
    accion: str,
    view: str,
    actor: "AbstractUser | None",
    estado_anterior: str,
    estado_nuevo: str,
) -> dict[str, Any]:
    rid = get_request_id()
    sol = estudio.solicitud
    muestra = estudio.muestra
    meta: dict[str, Any] = {
        "accion": accion,
        "estudio_id": estudio.pk,
        "numero_estudio": estudio.numero,
        "solicitud_id": sol.pk,
        "numero_solicitud": sol.numero,
        "muestra_id": muestra.pk,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
        "view": view,
    }
    if rid:
        meta["request_id"] = rid
    return meta


def _audit_estudio_update(
    estudio: EstudioMicrobiologia,
    *,
    before: dict[str, Any],
    actor: "AbstractUser | None",
    metadata: dict[str, Any],
) -> None:
    estudio.refresh_from_db()
    log_update(
        actor=actor,
        entity=estudio,
        before=before,
        module="laboratorio",
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Estudio: crear / iniciar / cancelar
# ---------------------------------------------------------------------------


def crear_estudio(
    *,
    solicitud,
    muestra,
    tipo_estudio: str,
    observaciones: str,
    actor: "AbstractUser | None",
    view: str,
) -> EstudioMicrobiologia:
    """Crea un estudio microbiológico en estado PENDIENTE.

    Valida:
    - muestra y solicitud coinciden;
    - paciente consistente;
    - muestra en RECIBIDA, CONSERVADA o EN_PROCESO;
    - solicitud no terminal (CANCELADO / VALIDADO / ENTREGADO).
    """
    if solicitud.estado in ("CANCELADO", "VALIDADO", "ENTREGADO"):
        raise MicrobiologiaAccionError(
            "No se puede crear un estudio sobre una solicitud cancelada, validada o entregada."
        )
    if muestra.estado not in MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO:
        raise MicrobiologiaAccionError(
            "Solo se puede iniciar microbiología sobre muestras RECIBIDA, CONSERVADA o EN_PROCESO."
        )
    if muestra.solicitud_id != solicitud.pk:
        raise MicrobiologiaAccionError(
            "La muestra no pertenece a la solicitud indicada."
        )

    with transaction.atomic():
        estudio = EstudioMicrobiologia(
            solicitud=solicitud,
            muestra=muestra,
            paciente_id=solicitud.paciente_id,
            tipo_estudio=tipo_estudio or "CULTIVO_RUTINA",
            observaciones=observaciones or "",
            estado="PENDIENTE",
        )
        estudio.save()
        meta = _base_estudio_metadata(
            estudio,
            accion="CREADA",
            view=view,
            actor=actor,
            estado_anterior="",
            estado_nuevo=estudio.estado,
        )
        log_create(actor=actor, entity=estudio, module="laboratorio", metadata=meta)
        return estudio


def aplicar_iniciar_estudio(
    estudio_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> EstudioMicrobiologia:
    """Transición PENDIENTE → RECIBIDO. Idempotente si ya está RECIBIDO."""
    with transaction.atomic():
        estudio = (
            EstudioMicrobiologia.objects.select_for_update()
            .select_related("solicitud", "muestra")
            .get(pk=estudio_id)
        )
        prev = estudio.estado
        if prev == "RECIBIDO":
            return estudio
        if prev != "PENDIENTE":
            raise MicrobiologiaAccionError(
                "Solo se puede iniciar un estudio en estado PENDIENTE."
            )
        before = safe_model_snapshot(estudio)
        estudio.estado = "RECIBIDO"
        estudio.fecha_inicio = timezone.now()
        if actor and getattr(actor, "is_authenticated", False) and not estudio.responsable_id:
            estudio.responsable = actor
        estudio.save()
        meta = _base_estudio_metadata(
            estudio,
            accion="iniciar",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=estudio.estado,
        )
        _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)
        return estudio


def aplicar_cancelar_estudio(
    estudio_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    motivo: str,
) -> EstudioMicrobiologia:
    """Cancela un estudio. Motivo obligatorio. No borra siembras ni lecturas."""
    if not (motivo or "").strip():
        raise MicrobiologiaAccionError("El motivo de cancelación es obligatorio.")
    with transaction.atomic():
        estudio = (
            EstudioMicrobiologia.objects.select_for_update()
            .select_related("solicitud", "muestra")
            .get(pk=estudio_id)
        )
        prev = estudio.estado
        if prev == "CANCELADO":
            raise MicrobiologiaAccionError("El estudio ya está cancelado.")
        before = safe_model_snapshot(estudio)
        estudio.estado = "CANCELADO"
        estudio.fecha_cancelacion = timezone.now()
        estudio.motivo_cancelacion = motivo.strip()
        if actor and getattr(actor, "is_authenticated", False):
            estudio.cancelado_por = actor
        estudio.save()
        meta = _base_estudio_metadata(
            estudio,
            accion="cancelar",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=estudio.estado,
        )
        meta["motivo_cancelacion_presente"] = bool(estudio.motivo_cancelacion)
        _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)
        return estudio


def _maybe_avanzar_estudio_a_sembrado(
    estudio: EstudioMicrobiologia,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> None:
    """Si el estudio está PENDIENTE o RECIBIDO, lo pasa a SEMBRADO. Idempotente."""
    if estudio.estado not in ("PENDIENTE", "RECIBIDO"):
        return
    prev = estudio.estado
    before = safe_model_snapshot(estudio)
    if not estudio.fecha_inicio:
        estudio.fecha_inicio = timezone.now()
    estudio.estado = "SEMBRADO"
    estudio.save()
    meta = _base_estudio_metadata(
        estudio,
        accion="auto_sembrado",
        view=view,
        actor=actor,
        estado_anterior=prev,
        estado_nuevo=estudio.estado,
    )
    _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)


def _maybe_avanzar_estudio_a_lectura_preliminar(
    estudio: EstudioMicrobiologia,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> None:
    """Si la lectura es preliminar y el estudio está SEMBRADO, transiciona a LECTURA_PRELIMINAR."""
    if estudio.estado != "SEMBRADO":
        return
    prev = estudio.estado
    before = safe_model_snapshot(estudio)
    estudio.estado = "LECTURA_PRELIMINAR"
    estudio.save()
    meta = _base_estudio_metadata(
        estudio,
        accion="auto_lectura_preliminar",
        view=view,
        actor=actor,
        estado_anterior=prev,
        estado_nuevo=estudio.estado,
    )
    _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)


def _maybe_avanzar_estudio_a_identificacion(
    estudio: EstudioMicrobiologia,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> None:
    """Avanza el estudio a IDENTIFICACION desde SEMBRADO o LECTURA_PRELIMINAR (B3.2)."""
    if estudio.estado not in ("SEMBRADO", "LECTURA_PRELIMINAR"):
        return
    prev = estudio.estado
    before = safe_model_snapshot(estudio)
    estudio.estado = "IDENTIFICACION"
    estudio.save()
    meta = _base_estudio_metadata(
        estudio,
        accion="auto_identificacion",
        view=view,
        actor=actor,
        estado_anterior=prev,
        estado_nuevo=estudio.estado,
    )
    _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)


def _maybe_avanzar_estudio_a_antibiograma(
    estudio: EstudioMicrobiologia,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> None:
    """Avanza el estudio a ANTIBIOGRAMA desde IDENTIFICACION / LECTURA_PRELIMINAR / SEMBRADO (B3.3).

    Idempotente: si ya está en ANTIBIOGRAMA o más allá, no hace nada.
    """
    if estudio.estado not in ("SEMBRADO", "LECTURA_PRELIMINAR", "IDENTIFICACION"):
        return
    prev = estudio.estado
    before = safe_model_snapshot(estudio)
    estudio.estado = "ANTIBIOGRAMA"
    estudio.save()
    meta = _base_estudio_metadata(
        estudio,
        accion="auto_antibiograma",
        view=view,
        actor=actor,
        estado_anterior=prev,
        estado_nuevo=estudio.estado,
    )
    _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)


# ---------------------------------------------------------------------------
# Siembras
# ---------------------------------------------------------------------------


def crear_siembra(
    *,
    estudio_id: int,
    medio_id: int,
    condicion_incubacion: str,
    temperatura_c,
    atmosfera: str,
    observaciones: str,
    fecha_siembra=None,
    actor: "AbstractUser | None",
    view: str,
) -> SiembraMicrobiologia:
    with transaction.atomic():
        estudio = (
            EstudioMicrobiologia.objects.select_for_update()
            .select_related("solicitud", "muestra")
            .get(pk=estudio_id)
        )
        if estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise MicrobiologiaAccionError("No se puede sembrar sobre un estudio cancelado.")
        try:
            medio = MedioCultivo.objects.get(pk=medio_id)
        except MedioCultivo.DoesNotExist as exc:
            raise MicrobiologiaAccionError("El medio de cultivo no existe.") from exc
        if not medio.activo:
            raise MicrobiologiaAccionError("El medio de cultivo debe estar activo.")
        if estudio.muestra.estado not in MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO:
            raise MicrobiologiaAccionError(
                "La muestra del estudio debe estar RECIBIDA, CONSERVADA o EN_PROCESO para sembrar."
            )

        siembra = SiembraMicrobiologia(
            estudio=estudio,
            muestra=estudio.muestra,
            medio=medio,
            fecha_siembra=fecha_siembra or timezone.now(),
            sembrado_por=actor if getattr(actor, "is_authenticated", False) else None,
            condicion_incubacion=condicion_incubacion or "",
            temperatura_c=temperatura_c,
            atmosfera=atmosfera or "",
            observaciones=observaciones or "",
            estado="SEMBRADA",
        )
        siembra.save()

        rid = get_request_id()
        meta = {
            "accion": "crear_siembra",
            "siembra_id": siembra.pk,
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
            "solicitud_id": estudio.solicitud_id,
            "numero_solicitud": estudio.solicitud.numero,
            "muestra_id": estudio.muestra_id,
            "medio_id": medio.pk,
            "observacion_presente": bool(siembra.observaciones),
            "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
            "view": view,
        }
        if rid:
            meta["request_id"] = rid
        log_create(actor=actor, entity=siembra, module="laboratorio", metadata=meta)

        _maybe_avanzar_estudio_a_sembrado(estudio, actor=actor, view=view)
        return siembra


# ---------------------------------------------------------------------------
# Lecturas
# ---------------------------------------------------------------------------


def crear_lectura(
    *,
    siembra_id: int,
    fecha_lectura=None,
    horas_incubacion=None,
    crecimiento: str,
    descripcion_colonias: str,
    tincion_gram: str,
    observaciones: str,
    es_preliminar: bool,
    actor: "AbstractUser | None",
    view: str,
) -> LecturaCultivo:
    with transaction.atomic():
        siembra = (
            SiembraMicrobiologia.objects.select_for_update()
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=siembra_id)
        )
        estudio = siembra.estudio
        if estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise MicrobiologiaAccionError("No se puede leer sobre un estudio cancelado.")
        if siembra.estado == "CANCELADA":
            raise MicrobiologiaAccionError("No se puede leer sobre una siembra cancelada.")

        lectura = LecturaCultivo(
            siembra=siembra,
            estudio=estudio,
            fecha_lectura=fecha_lectura or timezone.now(),
            leido_por=actor if getattr(actor, "is_authenticated", False) else None,
            horas_incubacion=horas_incubacion,
            crecimiento=crecimiento or "PENDIENTE",
            descripcion_colonias=descripcion_colonias or "",
            tincion_gram=tincion_gram or "",
            observaciones=observaciones or "",
            es_preliminar=bool(es_preliminar),
        )
        lectura.save()

        rid = get_request_id()
        meta = {
            "accion": "crear_lectura",
            "lectura_id": lectura.pk,
            "siembra_id": siembra.pk,
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
            "solicitud_id": estudio.solicitud_id,
            "numero_solicitud": estudio.solicitud.numero,
            "muestra_id": estudio.muestra_id,
            "crecimiento": lectura.crecimiento,
            "es_preliminar": lectura.es_preliminar,
            "resultado_presente": bool(
                lectura.descripcion_colonias or lectura.tincion_gram or lectura.observaciones
            ),
            "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
            "view": view,
        }
        if rid:
            meta["request_id"] = rid
        log_create(actor=actor, entity=lectura, module="laboratorio", metadata=meta)

        if lectura.es_preliminar:
            _maybe_avanzar_estudio_a_lectura_preliminar(estudio, actor=actor, view=view)
        return lectura


# ---------------------------------------------------------------------------
# B3.2 — Aislados e identificaciones
# ---------------------------------------------------------------------------


def _base_aislado_metadata(
    aislado: AisladoMicrobiologico,
    *,
    accion: str,
    view: str,
    actor: "AbstractUser | None",
    estado_anterior: str,
    estado_nuevo: str,
) -> dict[str, Any]:
    rid = get_request_id()
    estudio = aislado.estudio
    sol = estudio.solicitud
    muestra = estudio.muestra
    meta: dict[str, Any] = {
        "accion": accion,
        "aislado_id": aislado.pk,
        "estudio_id": estudio.pk,
        "numero_estudio": estudio.numero,
        "solicitud_id": sol.pk,
        "numero_solicitud": sol.numero,
        "muestra_id": muestra.pk,
        "lectura_id": aislado.lectura_origen_id,
        "microorganismo_id": aislado.microorganismo_id,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
        "view": view,
    }
    if rid:
        meta["request_id"] = rid
    return meta


def crear_aislado(
    *,
    estudio_id: int,
    lectura_id: int,
    microorganismo_id: int | None,
    descripcion: str,
    cantidad: str,
    significancia: str,
    requiere_antibiograma: bool,
    observaciones: str,
    actor: "AbstractUser | None",
    view: str,
) -> AisladoMicrobiologico:
    """Crea un aislado desde una lectura válida. Estado inicial: ``SOSPECHADO``.

    Si se pasa ``microorganismo_id`` y se desea estado ``IDENTIFICADO``, debe
    crearse luego una ``IdentificacionMicroorganismo`` (la creación del aislado
    no fuerza identificación: separa preselección de identificación formal).
    """
    with transaction.atomic():
        estudio = (
            EstudioMicrobiologia.objects.select_for_update()
            .select_related("solicitud", "muestra")
            .get(pk=estudio_id)
        )
        if estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise MicrobiologiaAccionError("No se puede crear aislado sobre un estudio cancelado.")
        try:
            lectura = LecturaCultivo.objects.select_related("siembra").get(pk=lectura_id)
        except LecturaCultivo.DoesNotExist as exc:
            raise MicrobiologiaAccionError("La lectura indicada no existe.") from exc
        if lectura.estudio_id != estudio.pk:
            raise MicrobiologiaAccionError("La lectura no pertenece al estudio indicado.")
        if lectura.siembra.estado == "CANCELADA":
            raise MicrobiologiaAccionError("No se puede crear aislado desde una lectura de siembra cancelada.")

        microorganismo = None
        if microorganismo_id:
            try:
                microorganismo = Microorganismo.objects.get(pk=microorganismo_id)
            except Microorganismo.DoesNotExist as exc:
                raise MicrobiologiaAccionError("El microorganismo no existe.") from exc
            if not microorganismo.activo:
                raise MicrobiologiaAccionError("El microorganismo debe estar activo.")

        aislado = AisladoMicrobiologico(
            estudio=estudio,
            lectura_origen=lectura,
            microorganismo=microorganismo,
            estado="SOSPECHADO",
            descripcion=descripcion or "",
            cantidad=cantidad or "",
            significancia=significancia or "NO_DEFINIDA",
            requiere_antibiograma=bool(requiere_antibiograma),
            observaciones=observaciones or "",
            creado_por=actor if getattr(actor, "is_authenticated", False) else None,
        )
        aislado.save()

        meta = _base_aislado_metadata(
            aislado,
            accion="crear_aislado",
            view=view,
            actor=actor,
            estado_anterior="",
            estado_nuevo=aislado.estado,
        )
        meta["requiere_antibiograma"] = aislado.requiere_antibiograma
        meta["significancia"] = aislado.significancia
        log_create(actor=actor, entity=aislado, module="laboratorio", metadata=meta)
        return aislado


def aplicar_descartar_aislado(
    aislado_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    motivo: str,
) -> AisladoMicrobiologico:
    """Descarta un aislado. Motivo obligatorio. Estado terminal del aislado."""
    if not (motivo or "").strip():
        raise MicrobiologiaAccionError("El motivo de descarte es obligatorio.")
    with transaction.atomic():
        aislado = (
            AisladoMicrobiologico.objects.select_for_update()
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=aislado_id)
        )
        prev = aislado.estado
        if prev == "DESCARTADO":
            raise MicrobiologiaAccionError("El aislado ya está descartado.")
        if aislado.estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise MicrobiologiaAccionError("No se puede operar sobre un estudio cancelado.")
        before = safe_model_snapshot(aislado)
        aislado.estado = "DESCARTADO"
        aislado.fecha_descarte = timezone.now()
        aislado.motivo_descarte = motivo.strip()
        if actor and getattr(actor, "is_authenticated", False):
            aislado.descartado_por = actor
        aislado.save()
        aislado.refresh_from_db()
        meta = _base_aislado_metadata(
            aislado,
            accion="descartar_aislado",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=aislado.estado,
        )
        meta["motivo_descarte_presente"] = bool(aislado.motivo_descarte)
        log_update(
            actor=actor,
            entity=aislado,
            before=before,
            module="laboratorio",
            metadata=meta,
        )
        return aislado


def crear_identificacion(
    *,
    aislado_id: int,
    microorganismo_id: int,
    metodo: str,
    resultado: str,
    confianza,
    fecha=None,
    observaciones: str,
    actor: "AbstractUser | None",
    view: str,
) -> IdentificacionMicroorganismo:
    """Crea una identificación; actualiza aislado y eventualmente estudio.

    - Microorganismo debe existir y estar activo.
    - Aislado no puede estar DESCARTADO.
    - Estudio no puede estar CANCELADO.
    - La primera identificación válida lleva el aislado a IDENTIFICADO (si estaba
      SOSPECHADO) y avanza el estudio a IDENTIFICACION cuando proceda.
    """
    with transaction.atomic():
        aislado = (
            AisladoMicrobiologico.objects.select_for_update()
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=aislado_id)
        )
        if aislado.estado in AisladoMicrobiologico.ESTADOS_BLOQUEAN_IDENTIFICACION:
            raise MicrobiologiaAccionError("No se puede identificar un aislado descartado.")
        estudio = aislado.estudio
        if estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise MicrobiologiaAccionError("No se puede identificar sobre un estudio cancelado.")
        try:
            microorganismo = Microorganismo.objects.get(pk=microorganismo_id)
        except Microorganismo.DoesNotExist as exc:
            raise MicrobiologiaAccionError("El microorganismo no existe.") from exc
        if not microorganismo.activo:
            raise MicrobiologiaAccionError("El microorganismo debe estar activo.")

        identificacion = IdentificacionMicroorganismo(
            aislado=aislado,
            microorganismo=microorganismo,
            metodo=metodo or "",
            resultado=resultado or "",
            confianza=confianza,
            fecha=fecha or timezone.now(),
            realizado_por=actor if getattr(actor, "is_authenticated", False) else None,
            observaciones=observaciones or "",
        )
        identificacion.save()

        rid = get_request_id()
        meta_create: dict[str, Any] = {
            "accion": "crear_identificacion",
            "identificacion_id": identificacion.pk,
            "aislado_id": aislado.pk,
            "microorganismo_id": microorganismo.pk,
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
            "solicitud_id": estudio.solicitud_id,
            "numero_solicitud": estudio.solicitud.numero,
            "muestra_id": estudio.muestra_id,
            "resultado_presente": bool(identificacion.resultado),
            "observacion_presente": bool(identificacion.observaciones),
            "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
            "view": view,
        }
        if rid:
            meta_create["request_id"] = rid
        log_create(actor=actor, entity=identificacion, module="laboratorio", metadata=meta_create)

        # Avanzar aislado si corresponde (SOSPECHADO → IDENTIFICADO).
        if aislado.estado == "SOSPECHADO":
            prev_aislado = aislado.estado
            before_aislado = safe_model_snapshot(aislado)
            aislado.microorganismo = microorganismo
            aislado.estado = "IDENTIFICADO"
            aislado.save()
            aislado.refresh_from_db()
            meta_aislado = _base_aislado_metadata(
                aislado,
                accion="auto_identificado",
                view=view,
                actor=actor,
                estado_anterior=prev_aislado,
                estado_nuevo=aislado.estado,
            )
            log_update(
                actor=actor,
                entity=aislado,
                before=before_aislado,
                module="laboratorio",
                metadata=meta_aislado,
            )
            _maybe_avanzar_estudio_a_identificacion(estudio, actor=actor, view=view)
        else:
            # Si el aislado ya estaba IDENTIFICADO, solo nos aseguramos de que el estudio
            # esté coherente (idempotente).
            _maybe_avanzar_estudio_a_identificacion(estudio, actor=actor, view=view)

        return identificacion


# ---------------------------------------------------------------------------
# B3.3 — Antibiograma microbiológico
# ---------------------------------------------------------------------------


def _base_antibiograma_metadata(
    antibiograma: Antibiograma,
    *,
    accion: str,
    view: str,
    actor: "AbstractUser | None",
    estado_anterior: str,
    estado_nuevo: str,
) -> dict[str, Any]:
    rid = get_request_id()
    aislado = antibiograma.aislado
    estudio = aislado.estudio
    sol = estudio.solicitud
    muestra = estudio.muestra
    meta: dict[str, Any] = {
        "accion": accion,
        "antibiograma_id": antibiograma.pk,
        "aislado_id": aislado.pk,
        "estudio_id": estudio.pk,
        "numero_estudio": estudio.numero,
        "solicitud_id": sol.pk,
        "numero_solicitud": sol.numero,
        "muestra_id": muestra.pk,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
        "view": view,
    }
    if rid:
        meta["request_id"] = rid
    return meta


def crear_antibiograma(
    *,
    aislado_id: int,
    metodo: str,
    fecha_inicio=None,
    observaciones: str,
    actor: "AbstractUser | None",
    view: str,
) -> Antibiograma:
    """Crea un antibiograma para un aislado IDENTIFICADO con microorganismo asignado.

    Reglas:
    - Aislado en estado ``IDENTIFICADO`` (no SOSPECHADO ni DESCARTADO).
    - Aislado con microorganismo asignado.
    - Estudio del aislado no CANCELADO.
    Estado inicial ``PENDIENTE``. Avanza el estudio a ``ANTIBIOGRAMA`` desde
    los estados aceptados (idempotente).
    """
    with transaction.atomic():
        try:
            aislado = (
                AisladoMicrobiologico.objects.select_for_update(of=("self",))
                .select_related("estudio", "estudio__solicitud", "estudio__muestra")
                .get(pk=aislado_id)
            )
        except AisladoMicrobiologico.DoesNotExist as exc:
            raise MicrobiologiaAccionError("El aislado indicado no existe.") from exc
        if aislado.estado != "IDENTIFICADO":
            raise MicrobiologiaAccionError(
                "Solo se puede crear antibiograma para aislados IDENTIFICADOS."
            )
        if not aislado.microorganismo_id:
            raise MicrobiologiaAccionError(
                "El aislado debe tener microorganismo asignado para antibiograma."
            )
        estudio = aislado.estudio
        if estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise MicrobiologiaAccionError(
                "No se puede crear antibiograma sobre un estudio cancelado."
            )

        antibiograma = Antibiograma(
            aislado=aislado,
            estado="PENDIENTE",
            metodo=metodo or "",
            fecha_inicio=fecha_inicio or timezone.now(),
            realizado_por=actor if getattr(actor, "is_authenticated", False) else None,
            observaciones=observaciones or "",
        )
        antibiograma.save()

        meta = _base_antibiograma_metadata(
            antibiograma,
            accion="crear_antibiograma",
            view=view,
            actor=actor,
            estado_anterior="",
            estado_nuevo=antibiograma.estado,
        )
        meta["microorganismo_id"] = aislado.microorganismo_id
        log_create(actor=actor, entity=antibiograma, module="laboratorio", metadata=meta)

        _maybe_avanzar_estudio_a_antibiograma(estudio, actor=actor, view=view)
        return antibiograma


def _maybe_avanzar_antibiograma_a_en_proceso(
    antibiograma: Antibiograma,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> None:
    """Si el antibiograma está PENDIENTE, lo pasa a EN_PROCESO al cargar el primer resultado."""
    if antibiograma.estado != "PENDIENTE":
        return
    prev = antibiograma.estado
    before = safe_model_snapshot(antibiograma)
    antibiograma.estado = "EN_PROCESO"
    antibiograma.save()
    antibiograma.refresh_from_db()
    meta = _base_antibiograma_metadata(
        antibiograma,
        accion="auto_en_proceso",
        view=view,
        actor=actor,
        estado_anterior=prev,
        estado_nuevo=antibiograma.estado,
    )
    log_update(
        actor=actor,
        entity=antibiograma,
        before=before,
        module="laboratorio",
        metadata=meta,
    )


def crear_resultado_antibiotico(
    *,
    antibiograma_id: int,
    antibiotico_id: int,
    halo_mm,
    mic: str,
    interpretacion: str,
    observaciones: str,
    actor: "AbstractUser | None",
    view: str,
) -> ResultadoAntibiotico:
    """Carga un resultado de antibiótico dentro de un antibiograma editable.

    Bloqueos:
    - Antibiograma COMPLETO o CANCELADO.
    - Antibiótico inactivo.
    - Antibiótico duplicado en el antibiograma (UniqueConstraint).
    """
    with transaction.atomic():
        try:
            antibiograma = (
                Antibiograma.objects.select_for_update(of=("self",))
                .select_related("aislado", "aislado__estudio", "aislado__estudio__solicitud", "aislado__estudio__muestra")
                .get(pk=antibiograma_id)
            )
        except Antibiograma.DoesNotExist as exc:
            raise MicrobiologiaAccionError("El antibiograma no existe.") from exc
        if antibiograma.estado in Antibiograma.ESTADOS_BLOQUEAN_CARGA:
            raise MicrobiologiaAccionError(
                "No se pueden cargar resultados en un antibiograma COMPLETO o CANCELADO."
            )
        try:
            antibiotico = Antibiotico.objects.get(pk=antibiotico_id)
        except Antibiotico.DoesNotExist as exc:
            raise MicrobiologiaAccionError("El antibiótico no existe.") from exc
        if not antibiotico.activo:
            raise MicrobiologiaAccionError("El antibiótico debe estar activo.")
        if ResultadoAntibiotico.objects.filter(
            antibiograma=antibiograma, antibiotico=antibiotico
        ).exists():
            raise MicrobiologiaAccionError(
                "Este antibiótico ya tiene un resultado en el antibiograma."
            )

        resultado = ResultadoAntibiotico(
            antibiograma=antibiograma,
            antibiotico=antibiotico,
            halo_mm=halo_mm,
            mic=mic or "",
            interpretacion=interpretacion,
            observaciones=observaciones or "",
        )
        resultado.save()

        rid = get_request_id()
        estudio = antibiograma.aislado.estudio
        meta = {
            "accion": "crear_resultado_antibiotico",
            "resultado_antibiotico_id": resultado.pk,
            "antibiograma_id": antibiograma.pk,
            "antibiotico_id": antibiotico.pk,
            "aislado_id": antibiograma.aislado_id,
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
            "solicitud_id": estudio.solicitud_id,
            "numero_solicitud": estudio.solicitud.numero,
            "muestra_id": estudio.muestra_id,
            "sensibilidad_presente": bool(resultado.interpretacion),
            "resultado_presente": bool(resultado.mic or resultado.halo_mm is not None),
            "observacion_presente": bool(resultado.observaciones),
            "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
            "view": view,
        }
        if rid:
            meta["request_id"] = rid
        log_create(actor=actor, entity=resultado, module="laboratorio", metadata=meta)

        _maybe_avanzar_antibiograma_a_en_proceso(antibiograma, actor=actor, view=view)
        antibiograma.refresh_from_db()
        _maybe_avanzar_estudio_a_antibiograma(estudio, actor=actor, view=view)
        return resultado


def actualizar_resultado_antibiotico(
    resultado_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    halo_mm=None,
    mic: str | None = None,
    interpretacion: str | None = None,
    observaciones: str | None = None,
) -> ResultadoAntibiotico:
    """PATCH controlado de un resultado: bloquea si antibiograma COMPLETO/CANCELADO."""
    with transaction.atomic():
        resultado = (
            ResultadoAntibiotico.objects.select_for_update(of=("self",))
            .select_related(
                "antibiograma",
                "antibiograma__aislado",
                "antibiograma__aislado__estudio",
                "antibiograma__aislado__estudio__solicitud",
                "antibiograma__aislado__estudio__muestra",
                "antibiotico",
            )
            .get(pk=resultado_id)
        )
        antibiograma = resultado.antibiograma
        if antibiograma.estado in Antibiograma.ESTADOS_BLOQUEAN_CARGA:
            raise MicrobiologiaAccionError(
                "No se pueden modificar resultados en un antibiograma COMPLETO o CANCELADO."
            )
        if not resultado.antibiotico.activo:
            # Defensivo: si el catálogo se desactivó después de la carga, no permitimos editar.
            raise MicrobiologiaAccionError(
                "El antibiótico asociado al resultado está inactivo; no se puede modificar."
            )
        before = safe_model_snapshot(resultado)
        if halo_mm is not None:
            resultado.halo_mm = halo_mm
        if mic is not None:
            resultado.mic = mic
        if interpretacion is not None:
            resultado.interpretacion = interpretacion
        if observaciones is not None:
            resultado.observaciones = observaciones
        resultado.save()
        resultado.refresh_from_db()

        rid = get_request_id()
        estudio = antibiograma.aislado.estudio
        meta = {
            "accion": "actualizar_resultado_antibiotico",
            "resultado_antibiotico_id": resultado.pk,
            "antibiograma_id": antibiograma.pk,
            "antibiotico_id": resultado.antibiotico_id,
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
            "solicitud_id": estudio.solicitud_id,
            "numero_solicitud": estudio.solicitud.numero,
            "muestra_id": estudio.muestra_id,
            "sensibilidad_presente": bool(resultado.interpretacion),
            "resultado_presente": bool(resultado.mic or resultado.halo_mm is not None),
            "observacion_presente": bool(resultado.observaciones),
            "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
            "view": view,
        }
        if rid:
            meta["request_id"] = rid
        log_update(
            actor=actor,
            entity=resultado,
            before=before,
            module="laboratorio",
            metadata=meta,
        )
        return resultado


def aplicar_completar_antibiograma(
    antibiograma_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> Antibiograma:
    """Marca el antibiograma como COMPLETO. Requiere al menos un resultado."""
    with transaction.atomic():
        antibiograma = (
            Antibiograma.objects.select_for_update(of=("self",))
            .select_related("aislado", "aislado__estudio", "aislado__estudio__solicitud", "aislado__estudio__muestra")
            .get(pk=antibiograma_id)
        )
        prev = antibiograma.estado
        if prev == "COMPLETO":
            raise MicrobiologiaAccionError("El antibiograma ya está COMPLETO.")
        if prev == "CANCELADO":
            raise MicrobiologiaAccionError("No se puede completar un antibiograma CANCELADO.")
        if not ResultadoAntibiotico.objects.filter(antibiograma=antibiograma).exists():
            raise MicrobiologiaAccionError(
                "No se puede completar un antibiograma sin resultados."
            )
        before = safe_model_snapshot(antibiograma)
        antibiograma.estado = "COMPLETO"
        antibiograma.fecha_resultado = timezone.now()
        antibiograma.save()
        antibiograma.refresh_from_db()
        meta = _base_antibiograma_metadata(
            antibiograma,
            accion="completar_antibiograma",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=antibiograma.estado,
        )
        log_update(
            actor=actor,
            entity=antibiograma,
            before=before,
            module="laboratorio",
            metadata=meta,
        )
        return antibiograma


def aplicar_cancelar_antibiograma(
    antibiograma_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    motivo: str,
) -> Antibiograma:
    """Cancela un antibiograma. Motivo obligatorio. No borra resultados."""
    if not (motivo or "").strip():
        raise MicrobiologiaAccionError("El motivo de cancelación es obligatorio.")
    with transaction.atomic():
        antibiograma = (
            Antibiograma.objects.select_for_update(of=("self",))
            .select_related("aislado", "aislado__estudio", "aislado__estudio__solicitud", "aislado__estudio__muestra")
            .get(pk=antibiograma_id)
        )
        prev = antibiograma.estado
        if prev == "CANCELADO":
            raise MicrobiologiaAccionError("El antibiograma ya está cancelado.")
        if prev == "COMPLETO":
            raise MicrobiologiaAccionError("No se puede cancelar un antibiograma COMPLETO.")
        before = safe_model_snapshot(antibiograma)
        antibiograma.estado = "CANCELADO"
        antibiograma.fecha_cancelacion = timezone.now()
        antibiograma.motivo_cancelacion = motivo.strip()
        if actor and getattr(actor, "is_authenticated", False):
            antibiograma.cancelado_por = actor
        antibiograma.save()
        antibiograma.refresh_from_db()
        meta = _base_antibiograma_metadata(
            antibiograma,
            accion="cancelar_antibiograma",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=antibiograma.estado,
        )
        meta["motivo_cancelacion_presente"] = bool(antibiograma.motivo_cancelacion)
        log_update(
            actor=actor,
            entity=antibiograma,
            before=before,
            module="laboratorio",
            metadata=meta,
        )
        return antibiograma


# ---------------------------------------------------------------------------
# B3.4 — Informes microbiológicos, validación y cierre
# ---------------------------------------------------------------------------


def _base_informe_metadata(
    informe: InformeMicrobiologia,
    *,
    accion: str,
    view: str,
    actor: "AbstractUser | None",
    estado_anterior: str,
    estado_nuevo: str,
) -> dict[str, Any]:
    rid = get_request_id()
    estudio = informe.estudio
    sol = estudio.solicitud
    muestra = estudio.muestra
    meta: dict[str, Any] = {
        "accion": accion,
        "informe_id": informe.pk,
        "tipo_informe": informe.tipo,
        "estudio_id": estudio.pk,
        "numero_estudio": estudio.numero,
        "solicitud_id": sol.pk,
        "numero_solicitud": sol.numero,
        "muestra_id": muestra.pk,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
        "view": view,
    }
    if rid:
        meta["request_id"] = rid
    return meta


def verificar_completitud_para_informe_final(estudio: EstudioMicrobiologia) -> None:
    """Reglas de completitud antes de emitir o validar un informe final.

    - Al menos una ``LecturaCultivo`` del estudio.
    - Aislados ``DESCARTADO`` no bloquean.
    - ``CONTAMINANTE`` / ``FLORA_HABITUAL`` en ``SOSPECHADO`` no exigen identificación.
    - Resto de ``SOSPECHADO`` bloquea.
    - ``IDENTIFICADO`` con ``requiere_antibiograma``: debe existir ``Antibiograma`` ``COMPLETO``.
    """
    if estudio.estado == "CANCELADO":
        raise MicrobiologiaAccionError("El estudio está cancelado.")
    if not LecturaCultivo.objects.filter(estudio_id=estudio.pk).exists():
        raise MicrobiologiaAccionError(
            "Se requiere al menos una lectura de cultivo antes del informe final."
        )
    lax_sign = frozenset({"CONTAMINANTE", "FLORA_HABITUAL"})
    for aislado in AisladoMicrobiologico.objects.filter(estudio_id=estudio.pk):
        if aislado.estado == "DESCARTADO":
            continue
        if aislado.estado == "SOSPECHADO" and aislado.significancia in lax_sign:
            continue
        if aislado.estado == "SOSPECHADO":
            raise MicrobiologiaAccionError(
                "Hay aislados sin identificar ni descartar que bloquean el informe final."
            )
        if aislado.estado == "IDENTIFICADO":
            if aislado.significancia in ("SIGNIFICATIVO", "CRITICO") and not aislado.microorganismo_id:
                raise MicrobiologiaAccionError(
                    "Un aislado significativo o crítico debe tener microorganismo asignado."
                )
            if aislado.requiere_antibiograma:
                ok = Antibiograma.objects.filter(
                    aislado_id=aislado.pk,
                    estado="COMPLETO",
                ).exists()
                if not ok:
                    raise MicrobiologiaAccionError(
                        "Un aislado que requiere antibiograma debe tener un antibiograma COMPLETO."
                    )


def crear_informe_borrador(
    *,
    estudio_id: int,
    tipo: str,
    texto: str,
    observaciones: str,
    reemplaza_a_id: int | None,
    actor: "AbstractUser | None",
    view: str,
) -> InformeMicrobiologia:
    """Crea un informe en estado BORRADOR."""
    with transaction.atomic():
        estudio = (
            EstudioMicrobiologia.objects.select_for_update(of=("self",))
            .select_related("solicitud", "muestra")
            .get(pk=estudio_id)
        )
        if estudio.estado == "CANCELADO":
            raise MicrobiologiaAccionError("No se puede crear informe sobre un estudio cancelado.")
        if estudio.estado in ("VALIDADO", "INFORMADO"):
            raise MicrobiologiaAccionError(
                "No se pueden crear informes sobre un estudio ya validado o informado."
            )
        if tipo == "FINAL":
            if InformeMicrobiologia.objects.filter(estudio_id=estudio.pk, tipo="FINAL").exclude(
                estado="ANULADO"
            ).exists():
                raise MicrobiologiaAccionError(
                    "Ya existe un informe final vigente para este estudio."
                )
            verificar_completitud_para_informe_final(estudio)
        reemplaza = None
        if reemplaza_a_id:
            try:
                reemplaza = InformeMicrobiologia.objects.get(pk=reemplaza_a_id, estudio_id=estudio.pk)
            except InformeMicrobiologia.DoesNotExist as exc:
                raise MicrobiologiaAccionError(
                    "El informe reemplazado no existe o no pertenece al estudio."
                ) from exc
        informe = InformeMicrobiologia(
            estudio=estudio,
            tipo=tipo,
            estado="BORRADOR",
            texto=texto or "",
            observaciones=observaciones or "",
            reemplaza_a=reemplaza,
        )
        informe.save()
        meta = _base_informe_metadata(
            informe,
            accion="crear_informe",
            view=view,
            actor=actor,
            estado_anterior="",
            estado_nuevo=informe.estado,
        )
        log_create(actor=actor, entity=informe, module="laboratorio", metadata=meta)
        return informe


def actualizar_informe_borrador(
    informe_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    texto: str | None = None,
    observaciones: str | None = None,
    version: int | None = None,
) -> InformeMicrobiologia:
    """PATCH solo en BORRADOR."""
    with transaction.atomic():
        informe = (
            InformeMicrobiologia.objects.select_for_update(of=("self",))
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=informe_id)
        )
        if informe.estado != "BORRADOR":
            raise MicrobiologiaAccionError("Solo se puede editar un informe en BORRADOR.")
        if informe.estudio.estado == "CANCELADO":
            raise MicrobiologiaAccionError("El estudio está cancelado.")
        before = safe_model_snapshot(informe)
        if texto is not None:
            informe.texto = texto
        if observaciones is not None:
            informe.observaciones = observaciones
        if version is not None:
            informe.version = version
        informe.save()
        informe.refresh_from_db()
        meta = _base_informe_metadata(
            informe,
            accion="actualizar_informe_borrador",
            view=view,
            actor=actor,
            estado_anterior="BORRADOR",
            estado_nuevo=informe.estado,
        )
        log_update(
            actor=actor,
            entity=informe,
            before=before,
            module="laboratorio",
            metadata=meta,
        )
        return informe


def _texto_efectivo_emitir(informe: InformeMicrobiologia, texto_payload: str | None) -> str:
    t = (texto_payload if texto_payload is not None else informe.texto) or ""
    return t.strip()


def aplicar_emitir_informe(
    informe_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    texto: str | None = None,
) -> InformeMicrobiologia:
    """Emite un informe (preliminar o final). Texto obligatorio no vacío."""
    with transaction.atomic():
        informe = (
            InformeMicrobiologia.objects.select_for_update(of=("self",))
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=informe_id)
        )
        if informe.estado != "BORRADOR":
            raise MicrobiologiaAccionError("Solo se puede emitir un informe en BORRADOR.")
        estudio = informe.estudio
        if estudio.estado == "CANCELADO":
            raise MicrobiologiaAccionError("El estudio está cancelado.")
        if estudio.estado in ("VALIDADO", "INFORMADO"):
            raise MicrobiologiaAccionError("El estudio ya está validado o informado.")
        texto_ok = _texto_efectivo_emitir(informe, texto)
        if not texto_ok:
            raise MicrobiologiaAccionError("El texto del informe es obligatorio al emitir.")
        prev_inf = informe.estado
        before_inf = safe_model_snapshot(informe)
        informe.texto = texto_ok
        informe.estado = "EMITIDO"
        informe.fecha_emision = timezone.now()
        if actor and getattr(actor, "is_authenticated", False):
            informe.emitido_por = actor
        informe.save()
        informe.refresh_from_db()
        meta_inf = _base_informe_metadata(
            informe,
            accion="emitir_informe",
            view=view,
            actor=actor,
            estado_anterior=prev_inf,
            estado_nuevo=informe.estado,
        )
        log_update(
            actor=actor,
            entity=informe,
            before=before_inf,
            module="laboratorio",
            metadata=meta_inf,
        )

        if informe.tipo == "FINAL":
            verificar_completitud_para_informe_final(estudio)
            prev_es = estudio.estado
            if estudio.estado not in ("VALIDADO", "INFORMADO", "LISTO_PARA_VALIDAR"):
                before_es = safe_model_snapshot(estudio)
                estudio.estado = "LISTO_PARA_VALIDAR"
                estudio.save()
                estudio.refresh_from_db()
                meta_es = _base_estudio_metadata(
                    estudio,
                    accion="auto_listo_para_validar",
                    view=view,
                    actor=actor,
                    estado_anterior=prev_es,
                    estado_nuevo=estudio.estado,
                )
                _audit_estudio_update(estudio, before=before_es, actor=actor, metadata=meta_es)
        return informe


def aplicar_validar_informe_final(
    informe_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> InformeMicrobiologia:
    """Valida el informe final emitido y el estudio (solo invocado con permiso admin)."""
    with transaction.atomic():
        informe = (
            InformeMicrobiologia.objects.select_for_update(of=("self",))
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=informe_id)
        )
        if informe.tipo != "FINAL":
            raise MicrobiologiaAccionError("Solo se puede validar un informe FINAL.")
        if informe.estado != "EMITIDO":
            raise MicrobiologiaAccionError("Solo se puede validar un informe EMITIDO.")
        estudio = informe.estudio
        if estudio.estado != "LISTO_PARA_VALIDAR":
            raise MicrobiologiaAccionError(
                "El estudio debe estar LISTO_PARA_VALIDAR para validar el informe final."
            )
        verificar_completitud_para_informe_final(estudio)
        prev_inf = informe.estado
        before_inf = safe_model_snapshot(informe)
        informe.estado = "VALIDADO"
        informe.fecha_validacion = timezone.now()
        if actor and getattr(actor, "is_authenticated", False):
            informe.validado_por = actor
        informe.save()
        informe.refresh_from_db()
        meta_inf = _base_informe_metadata(
            informe,
            accion="validar_informe",
            view=view,
            actor=actor,
            estado_anterior=prev_inf,
            estado_nuevo=informe.estado,
        )
        log_update(
            actor=actor,
            entity=informe,
            before=before_inf,
            module="laboratorio",
            metadata=meta_inf,
        )

        prev_es = estudio.estado
        before_es = safe_model_snapshot(estudio)
        estudio.estado = "VALIDADO"
        if not estudio.fecha_cierre:
            estudio.fecha_cierre = timezone.now()
        estudio.save()
        estudio.refresh_from_db()
        meta_es = _base_estudio_metadata(
            estudio,
            accion="auto_validado_informe_final",
            view=view,
            actor=actor,
            estado_anterior=prev_es,
            estado_nuevo=estudio.estado,
        )
        _audit_estudio_update(estudio, before=before_es, actor=actor, metadata=meta_es)
        return informe


def aplicar_anular_informe(
    informe_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
    motivo: str,
) -> InformeMicrobiologia:
    """Anula un informe en BORRADOR o EMITIDO (no VALIDADO). Motivo obligatorio."""
    if not (motivo or "").strip():
        raise MicrobiologiaAccionError("El motivo de anulación es obligatorio.")
    with transaction.atomic():
        informe = (
            InformeMicrobiologia.objects.select_for_update(of=("self",))
            .select_related("estudio", "estudio__solicitud", "estudio__muestra")
            .get(pk=informe_id)
        )
        if informe.estado == "ANULADO":
            raise MicrobiologiaAccionError("El informe ya está anulado.")
        if informe.estado == "VALIDADO":
            raise MicrobiologiaAccionError("No se puede anular un informe VALIDADO.")
        prev_inf = informe.estado
        before_inf = safe_model_snapshot(informe)
        informe.estado = "ANULADO"
        informe.motivo_anulacion = motivo.strip()
        informe.fecha_anulacion = timezone.now()
        if actor and getattr(actor, "is_authenticated", False):
            informe.anulado_por = actor
        informe.save()
        informe.refresh_from_db()
        meta_inf = _base_informe_metadata(
            informe,
            accion="anular_informe",
            view=view,
            actor=actor,
            estado_anterior=prev_inf,
            estado_nuevo=informe.estado,
        )
        meta_inf["motivo_anulacion_presente"] = bool(informe.motivo_anulacion)
        log_update(
            actor=actor,
            entity=informe,
            before=before_inf,
            module="laboratorio",
            metadata=meta_inf,
        )
        return informe


def aplicar_marcar_estudio_informado(
    estudio_id: int,
    *,
    actor: "AbstractUser | None",
    view: str,
) -> EstudioMicrobiologia:
    """Marca el estudio como INFORMADO (requiere estudio VALIDADO)."""
    with transaction.atomic():
        estudio = (
            EstudioMicrobiologia.objects.select_for_update(of=("self",))
            .select_related("solicitud", "muestra")
            .get(pk=estudio_id)
        )
        if estudio.estado != "VALIDADO":
            raise MicrobiologiaAccionError(
                "Solo se puede marcar como informado un estudio en estado VALIDADO."
            )
        if not InformeMicrobiologia.objects.filter(
            estudio_id=estudio.pk,
            tipo="FINAL",
            estado="VALIDADO",
        ).exists():
            raise MicrobiologiaAccionError(
                "Debe existir un informe final VALIDADO antes de marcar el estudio como informado."
            )
        prev = estudio.estado
        before = safe_model_snapshot(estudio)
        estudio.estado = "INFORMADO"
        estudio.save()
        estudio.refresh_from_db()
        meta = _base_estudio_metadata(
            estudio,
            accion="marcar_informado",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=estudio.estado,
        )
        _audit_estudio_update(estudio, before=before, actor=actor, metadata=meta)
        return estudio
