"""
Transiciones de estado controladas para Muestra (LIMS Fase B1).
Los cambios de estado solo ocurren vía acciones explícitas (servicio / ViewSet).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.utils import timezone

from auditoria.audit_service import log_update
from auditoria.context import get_request_id
from auditoria.snapshot import safe_model_snapshot

from laboratorio.models import SolicitudExamen
from laboratorio.models_catalog import EventoMuestra, Muestra
from laboratorio.solicitud_estado import (
    SolicitudEstadoTransitionError,
    apply_solicitud_estado_transition,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class MuestraAccionError(ValueError):
    """Acción o transición no permitida sobre la muestra."""


_TERMINAL_NO_OP = frozenset({"RECHAZADA", "DESCARTADA", "CANCELADA"})


def crear_muestra(
    *,
    solicitud: SolicitudExamen,
    tipo_muestra_id: int,
    tipo_contenedor_id: int | None,
    observaciones: str,
    actor: AbstractUser | None,
    view: str,
    codigo_barra: str | None = None,
) -> Muestra:
    """Crea muestra en PENDIENTE_TOMA, evento CREADA y auditoría CREATE."""
    from auditoria.audit_service import log_create

    with transaction.atomic():
        muestra = Muestra(
            solicitud=solicitud,
            paciente_id=solicitud.paciente_id,
            tipo_muestra_id=tipo_muestra_id,
            tipo_contenedor_id=tipo_contenedor_id,
            observaciones=observaciones or "",
            estado="PENDIENTE_TOMA",
            codigo_barra=(codigo_barra or "").strip() or None,
        )
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_create",
            view=view,
            actor=actor,
            estado_anterior="",
            estado_nuevo=muestra.estado,
        )
        _append_evento(
            muestra,
            accion="CREADA",
            estado_anterior="",
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones="",
            metadata=meta,
        )
        log_create(actor=actor, entity=muestra, module="laboratorio", metadata=meta)
        return muestra


def _base_metadata(
    muestra: Muestra,
    *,
    accion: str,
    view: str,
    actor: AbstractUser | None,
    estado_anterior: str,
    estado_nuevo: str,
) -> dict[str, Any]:
    sol = muestra.solicitud
    rid = get_request_id()
    meta: dict[str, Any] = {
        "accion": accion,
        "muestra_id": muestra.pk,
        "solicitud_id": sol.pk,
        "numero_solicitud": sol.numero,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "tipo_muestra_id": muestra.tipo_muestra_id,
        "actor_id": getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None,
        "view": view,
    }
    if rid:
        meta["request_id"] = rid
    return meta


def _append_evento(
    muestra: Muestra,
    *,
    accion: str,
    estado_anterior: str,
    estado_nuevo: str,
    actor: AbstractUser | None,
    observaciones: str,
    metadata: dict[str, Any],
) -> EventoMuestra:
    rid = get_request_id() or ""
    return EventoMuestra.objects.create(
        muestra=muestra,
        accion=accion,
        estado_anterior=estado_anterior or "",
        estado_nuevo=estado_nuevo or "",
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        observaciones=observaciones or "",
        metadata=metadata,
        request_id=rid[:64] if rid else "",
    )


def _audit_muestra_update(
    muestra: Muestra,
    *,
    before: dict[str, Any],
    actor: AbstractUser | None,
    metadata: dict[str, Any],
) -> None:
    muestra.refresh_from_db()
    log_update(
        actor=actor,
        entity=muestra,
        before=before,
        module="laboratorio",
        metadata=metadata,
    )


def _maybe_coordina_solicitud_toma_muestra(
    solicitud: SolicitudExamen,
    *,
    actor: AbstractUser | None,
    view: str,
    muestra: Muestra,
) -> None:
    if solicitud.estado != "PENDIENTE":
        return
    try:
        apply_solicitud_estado_transition(
            solicitud,
            "EN_PROCESO",
            actor=actor,
            accion="tomar_muestra",
            view=view,
            extra_metadata={
                "muestra_id": muestra.pk,
            },
        )
    except SolicitudEstadoTransitionError:
        pass


def aplicar_tomar(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    observaciones: str = "",
) -> Muestra:
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev != "PENDIENTE_TOMA":
            raise MuestraAccionError("Solo se puede tomar una muestra pendiente de toma.")
        before = safe_model_snapshot(muestra)
        now = timezone.now()
        muestra.estado = "TOMADA"
        muestra.fecha_toma = now
        muestra.tomada_por = actor if getattr(actor, "is_authenticated", False) else None
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        sol = SolicitudExamen.objects.select_for_update().get(pk=muestra.solicitud_id)
        _maybe_coordina_solicitud_toma_muestra(sol, actor=actor, view=view, muestra=muestra)
        meta = _base_metadata(
            muestra,
            accion="muestra_tomar",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        _append_evento(
            muestra,
            accion="TOMADA",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


_MUESTRA_ESTADOS_TERMINALES = frozenset({"RECHAZADA", "DESCARTADA", "CANCELADA"})


def _tipos_muestra_requeridos_por_solicitud(solicitud: SolicitudExamen) -> set[int]:
    return set(
        solicitud.tipos_examen.filter(activo=True).values_list(
            "tipo_muestra_requerida_id", flat=True
        )
    )


def tomar_muestras_en_solicitud(
    solicitud_id: int,
    *,
    items: list[dict[str, Any]],
    actor: AbstractUser | None,
    view: str,
) -> SolicitudExamen:
    """
    Crea muestras físicas, las marca TOMADA y coordina PENDIENTE → EN_PROCESO.
    Sin ítems, solo transiciona la orden (compatibilidad legacy).
    """
    with transaction.atomic():
        solicitud = (
            SolicitudExamen.objects.select_for_update()
            .prefetch_related("tipos_examen")
            .get(pk=solicitud_id)
        )
        if solicitud.estado != "PENDIENTE":
            raise SolicitudEstadoTransitionError(
                "Solo se puede tomar muestra cuando la solicitud está pendiente."
            )

        if not items:
            apply_solicitud_estado_transition(
                solicitud,
                "EN_PROCESO",
                actor=actor,
                accion="tomar_muestra",
                view=view,
            )
            return solicitud

        vistos: set[int] = set()
        for item in items:
            tm_id = int(item["tipo_muestra_id"])
            if tm_id in vistos:
                raise MuestraAccionError("No se puede repetir el mismo tipo de muestra.")
            vistos.add(tm_id)
            from laboratorio.models import TipoMuestra

            try:
                tm = TipoMuestra.objects.get(pk=tm_id)
            except TipoMuestra.DoesNotExist as exc:
                raise MuestraAccionError("Tipo de muestra inexistente.") from exc
            if not tm.activo:
                raise MuestraAccionError("El tipo de muestra seleccionado está inactivo.")
            if Muestra.objects.filter(
                solicitud_id=solicitud.pk,
                tipo_muestra_id=tm_id,
            ).exclude(estado__in=_MUESTRA_ESTADOS_TERMINALES).exists():
                raise MuestraAccionError(
                    "Ya existe una muestra activa de ese tipo para esta orden."
                )
            muestra = crear_muestra(
                solicitud=solicitud,
                tipo_muestra_id=tm_id,
                tipo_contenedor_id=item.get("tipo_contenedor_id"),
                observaciones=item.get("observaciones") or "",
                actor=actor,
                view=view,
            )
            aplicar_tomar(
                muestra.pk,
                actor=actor,
                view=view,
                observaciones=item.get("observaciones") or "",
            )
            aplicar_recibir(
                muestra.pk,
                actor=actor,
                view=view,
                observaciones="Recepción automática al tomar muestra en la orden.",
                ubicacion_actual=item.get("ubicacion_actual") or "Laboratorio",
            )

        solicitud.refresh_from_db()
        if solicitud.estado == "PENDIENTE":
            apply_solicitud_estado_transition(
                solicitud,
                "EN_PROCESO",
                actor=actor,
                accion="tomar_muestra",
                view=view,
            )
        return solicitud


def aplicar_recibir(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    observaciones: str = "",
    ubicacion_actual: str = "",
) -> Muestra:
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev in _TERMINAL_NO_OP:
            raise MuestraAccionError("No se puede recibir una muestra en estado terminal.")
        if prev != "TOMADA":
            raise MuestraAccionError("Solo se pueden recibir muestras ya tomadas (no recepción directa en esta fase).")
        before = safe_model_snapshot(muestra)
        now = timezone.now()
        muestra.estado = "RECIBIDA"
        muestra.fecha_recepcion = now
        muestra.recibida_por = actor if getattr(actor, "is_authenticated", False) else None
        if ubicacion_actual:
            muestra.ubicacion_actual = ubicacion_actual
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_recibir",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        _append_evento(
            muestra,
            accion="RECIBIDA",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def aplicar_iniciar_proceso(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    observaciones: str = "",
    resultado_id: int | None = None,
) -> Muestra:
    """
    Transición RECIBIDA/CONSERVADA → EN_PROCESO (LIMS Fase B2).

    - Idempotente: si la muestra ya está EN_PROCESO, no genera evento ni auditoría.
    - Disparada desde cargar-resultados al asociar el primer resultado.
    """
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev == "EN_PROCESO":
            return muestra
        if prev not in ("RECIBIDA", "CONSERVADA"):
            raise MuestraAccionError(
                "Solo se puede iniciar el procesamiento de una muestra recibida o conservada."
            )
        before = safe_model_snapshot(muestra)
        muestra.estado = "EN_PROCESO"
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_procesamiento",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        if resultado_id is not None:
            meta["resultado_id"] = resultado_id
        _append_evento(
            muestra,
            accion="PROCESAMIENTO",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def aplicar_rechazar(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    motivo_rechazo: str,
    observaciones: str = "",
) -> Muestra:
    if not (motivo_rechazo or "").strip():
        raise MuestraAccionError("El motivo de rechazo es obligatorio.")
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        if muestra.resultados.exists():
            raise MuestraAccionError(
                "No se puede rechazar una muestra con resultados asociados."
            )
        prev = muestra.estado
        if prev in ("DESCARTADA", "CANCELADA"):
            raise MuestraAccionError("No se puede rechazar una muestra descartada o cancelada.")
        if prev == "RECHAZADA":
            raise MuestraAccionError("La muestra ya está rechazada.")
        before = safe_model_snapshot(muestra)
        now = timezone.now()
        muestra.estado = "RECHAZADA"
        muestra.fecha_rechazo = now
        muestra.rechazada_por = actor if getattr(actor, "is_authenticated", False) else None
        muestra.motivo_rechazo = motivo_rechazo.strip()
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_rechazar",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        meta["motivo_presente"] = bool(motivo_rechazo.strip())
        _append_evento(
            muestra,
            accion="RECHAZADA",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones or "",
            metadata={**meta, "motivo_presente": True},
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def aplicar_conservar(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    ubicacion_actual: str = "",
    observaciones: str = "",
) -> Muestra:
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev in _TERMINAL_NO_OP:
            raise MuestraAccionError("No se puede conservar una muestra en estado terminal.")
        if prev not in ("RECIBIDA", "EN_PROCESO"):
            raise MuestraAccionError("Solo se pueden conservar muestras recibidas o en proceso.")
        before = safe_model_snapshot(muestra)
        now = timezone.now()
        muestra.estado = "CONSERVADA"
        muestra.fecha_conservacion = now
        if ubicacion_actual:
            muestra.ubicacion_actual = ubicacion_actual
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_conservar",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        _append_evento(
            muestra,
            accion="CONSERVADA",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def aplicar_descartar(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    observaciones: str = "",
) -> Muestra:
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev in _TERMINAL_NO_OP:
            raise MuestraAccionError("No se puede descartar una muestra en estado terminal incompatible.")
        if prev not in ("RECIBIDA", "CONSERVADA"):
            raise MuestraAccionError("Solo se pueden descartar muestras recibidas o conservadas.")
        before = safe_model_snapshot(muestra)
        now = timezone.now()
        muestra.estado = "DESCARTADA"
        muestra.fecha_descarte = now
        muestra.descartada_por = actor if getattr(actor, "is_authenticated", False) else None
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_descartar",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        _append_evento(
            muestra,
            accion="DESCARTADA",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def aplicar_cancelar(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    motivo: str = "",
    observaciones: str = "",
) -> Muestra:
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev in ("DESCARTADA", "CANCELADA", "RECHAZADA"):
            raise MuestraAccionError("No se puede cancelar la muestra en su estado actual.")
        before = safe_model_snapshot(muestra)
        muestra.estado = "CANCELADA"
        if motivo:
            muestra.observaciones = (
                (muestra.observaciones + "\n" if muestra.observaciones else "")
                + "[Cancelación] "
                + motivo.strip()
            )
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="CANCELADA",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        _append_evento(
            muestra,
            accion="CANCELADA",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones or motivo,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def aplicar_cambiar_ubicacion(
    muestra_id: int,
    *,
    actor: AbstractUser | None,
    view: str,
    ubicacion_actual: str,
    observaciones: str = "",
) -> Muestra:
    ubicacion = (ubicacion_actual or "").strip()
    if not ubicacion:
        raise MuestraAccionError("La ubicación es obligatoria.")
    with transaction.atomic():
        muestra = Muestra.objects.select_for_update().select_related("solicitud").get(pk=muestra_id)
        prev = muestra.estado
        if prev in _TERMINAL_NO_OP:
            raise MuestraAccionError("No se puede cambiar ubicación en estado terminal.")
        if prev not in ("RECIBIDA", "CONSERVADA"):
            raise MuestraAccionError(
                "Solo se puede cambiar ubicación de muestras recibidas o conservadas."
            )
        before = safe_model_snapshot(muestra)
        muestra.ubicacion_actual = ubicacion
        if observaciones:
            muestra.observaciones = (muestra.observaciones + "\n" if muestra.observaciones else "") + observaciones
        muestra.save()
        meta = _base_metadata(
            muestra,
            accion="muestra_cambiar_ubicacion",
            view=view,
            actor=actor,
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
        )
        meta["ubicacion_nueva"] = ubicacion
        _append_evento(
            muestra,
            accion="CAMBIO_UBICACION",
            estado_anterior=prev,
            estado_nuevo=muestra.estado,
            actor=actor,
            observaciones=observaciones,
            metadata=meta,
        )
        _audit_muestra_update(muestra, before=before, actor=actor, metadata=meta)
        return muestra


def registrar_evento_actualizacion_admin(
    muestra: Muestra,
    *,
    actor: AbstractUser | None,
    view: str,
    estado_anterior: str,
) -> None:
    meta = _base_metadata(
        muestra,
        accion="ACTUALIZADA",
        view=view,
        actor=actor,
        estado_anterior=estado_anterior,
        estado_nuevo=muestra.estado,
    )
    _append_evento(
        muestra,
        accion="ACTUALIZADA",
        estado_anterior=estado_anterior,
        estado_nuevo=muestra.estado,
        actor=actor,
        observaciones="",
        metadata=meta,
    )
