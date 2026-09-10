"""Worklist e ingesta de analizadores (CM260 / Sysmex XP-300)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from auditoria.audit_service import log_event
from laboratorio.instrumentos_catalogo import normalizar_codigo_analito
from laboratorio.lab_codigo import CodigoKind, codigo_instrumento_desde_tubo, parse_codigo
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.models_instrumentos import (
    InterfazInstrumento,
    MapeoAnalitoInstrumento,
    MensajeInstrumento,
)
from laboratorio.qc_service import QcGateError, verificar_iqc_para_solicitud
from laboratorio.resultado_carga import CargaResultadosError, ESTADOS_CARGABLES, cargar_resultados_solicitud
from laboratorio.entrada_resultados import quantize_valor_numerico

logger = logging.getLogger(__name__)

MUESTRA_ESTADOS_WORKLIST = frozenset({"RECIBIDA", "CONSERVADA", "EN_PROCESO"})
CRUDO_MAX = 4000


class InstrumentoError(Exception):
    def __init__(self, message: str, *, estado: str = MensajeInstrumento.Estado.ERROR):
        super().__init__(message)
        self.estado = estado


@dataclass
class AnalitoWorklist:
    codigo_instrumento: str
    tipo_examen_codigo: str
    tipo_examen_id: int
    resultado_id: int


@dataclass
class WorklistResult:
    estado: str
    sample_id: str
    interfaz: InterfazInstrumento
    muestra: Muestra | None = None
    solicitud: SolicitudExamen | None = None
    paciente_apellido: str = ""
    paciente_nombre: str = ""
    paciente_dni: str = ""
    numero_solicitud: str = ""
    analitos: list[AnalitoWorklist] = field(default_factory=list)
    detalle: str = ""


@dataclass
class IngestaItem:
    codigo_instrumento: str
    valor: str
    unidad: str = ""


@dataclass
class IngestaResult:
    estado: str
    sample_id: str
    interfaz: InterfazInstrumento
    muestra: Muestra | None = None
    solicitud: SolicitudExamen | None = None
    cargados: int = 0
    sin_match: list[str] = field(default_factory=list)
    detalle: str = ""


def _actor_db(actor):
    if actor is None or getattr(actor, "pk", None) is None:
        return None
    return actor


def _truncar_crudo(crudo: str | None) -> str:
    text = crudo or ""
    if len(text) <= CRUDO_MAX:
        return text
    return text[:CRUDO_MAX] + "…"


def _auditar_mensaje(msg: MensajeInstrumento, actor=None) -> None:
    log_event(
        actor=actor,
        action="instrumento",
        entity=msg,
        module="laboratorio",
        metadata={
            "accion": "mensaje_instrumento",
            "interfaz_id": msg.interfaz_id,
            "estado": msg.estado,
            "direccion": msg.direccion,
            "muestra_id": msg.muestra_id,
            "solicitud_id": msg.solicitud_id,
            "sample_id_presente": bool(msg.sample_id),
            "valor_presente": False,
        },
    )


def registrar_mensaje(
    *,
    interfaz: InterfazInstrumento,
    direccion: str,
    estado: str,
    sample_id: str = "",
    crudo: str = "",
    detalle: str = "",
    muestra: Muestra | None = None,
    solicitud: SolicitudExamen | None = None,
    actor=None,
) -> MensajeInstrumento:
    msg = MensajeInstrumento.objects.create(
        interfaz=interfaz,
        direccion=direccion,
        estado=estado,
        sample_id=(sample_id or "")[:32],
        crudo=_truncar_crudo(crudo),
        detalle=(detalle or "")[:255],
        muestra=muestra,
        solicitud=solicitud,
    )
    try:
        _auditar_mensaje(msg, actor=actor)
    except Exception:
        logger.exception("auditoría mensaje instrumento %s", msg.pk)
    return msg


def resolver_interfaz(
    *,
    interfaz_id: int | None = None,
    equipo_codigo: str | None = None,
    driver: str | None = None,
) -> InterfazInstrumento:
    qs = InterfazInstrumento.objects.select_related("equipo").filter(activo=True)
    if interfaz_id:
        obj = qs.filter(pk=interfaz_id).first()
        if obj is None:
            raise InstrumentoError("Interfaz de analizador no encontrada o inactiva.")
        return obj
    if driver:
        obj = qs.filter(driver=driver).first()
        if obj is None:
            raise InstrumentoError(f"No hay interfaz activa para driver {driver}.")
        return obj
    if equipo_codigo:
        from laboratorio.equipos_lab import codigo_equipo_canonico

        canon = codigo_equipo_canonico(equipo_codigo)
        obj = qs.filter(equipo__codigo__iexact=canon).first() or qs.filter(
            equipo__codigo__iexact=equipo_codigo
        ).first()
        if obj is None:
            raise InstrumentoError(f"No hay interfaz activa para equipo {equipo_codigo}.")
        return obj
    raise InstrumentoError("Indique interfaz_id, equipo_codigo o driver.")


def resolver_muestra_por_sample_id(sample_id: str | None) -> Muestra | None:
    raw = (sample_id or "").strip()
    if not raw:
        return None
    qs = Muestra.objects.select_related("solicitud", "solicitud__paciente", "tipo_contenedor")
    found = qs.filter(codigo_barra__iexact=raw).first()
    if found:
        return found
    found = qs.filter(codigo_instrumento__iexact=raw).first()
    if found:
        return found
    compact = codigo_instrumento_desde_tubo(raw)
    if compact and compact.upper() != raw.upper():
        found = qs.filter(codigo_instrumento__iexact=compact).first()
        if found:
            return found
    parsed = parse_codigo(raw)
    if parsed.kind == CodigoKind.TUBO:
        return qs.filter(codigo_barra__iexact=parsed.raw).first()
    return None


def _mapeos_activos(interfaz: InterfazInstrumento) -> dict[str, MapeoAnalitoInstrumento]:
    rows = MapeoAnalitoInstrumento.objects.filter(
        interfaz=interfaz, activo=True
    ).select_related("tipo_examen")
    return {normalizar_codigo_analito(r.codigo_instrumento): r for r in rows}


def _mapeos_por_tipo_examen(interfaz: InterfazInstrumento) -> dict[int, str]:
    """tipo_examen_id → primer código de instrumento."""
    out: dict[int, str] = {}
    for codigo, mapeo in _mapeos_activos(interfaz).items():
        out.setdefault(mapeo.tipo_examen_id, codigo)
    return out


def _resultado_pertenece_al_tubo(resultado: ResultadoExamen, muestra: Muestra) -> bool:
    if resultado.muestra_id == muestra.pk:
        return True
    if resultado.muestra_id:
        return False
    te = resultado.tipo_examen
    if te.tipo_contenedor_id and muestra.tipo_contenedor_id:
        return te.tipo_contenedor_id == muestra.tipo_contenedor_id
    if te.tipo_contenedor_id and not muestra.tipo_contenedor_id:
        return False
    return True


def _pendientes_tubo(muestra: Muestra, interfaz: InterfazInstrumento) -> list[ResultadoExamen]:
    solicitud = muestra.solicitud
    equipo_id = interfaz.equipo_id
    qs = (
        ResultadoExamen.objects.select_related("tipo_examen", "tipo_examen__tipo_contenedor")
        .filter(solicitud=solicitud, tipo_examen__equipo_analizador_id=equipo_id)
        .filter(tipo_examen__activo=True)
    )
    out: list[ResultadoExamen] = []
    for r in qs:
        if (r.valor_obtenido or "").strip():
            continue
        if r.validado_por_id or r.fecha_validacion:
            continue
        if not _resultado_pertenece_al_tubo(r, muestra):
            continue
        out.append(r)
    return out


def consulta_trabajo(
    *,
    sample_id: str,
    interfaz: InterfazInstrumento,
    actor=None,
    crudo: str = "",
) -> WorklistResult:
    interfaz.tocar()
    actor = _actor_db(actor)
    muestra = resolver_muestra_por_sample_id(sample_id)
    if muestra is None:
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=MensajeInstrumento.Estado.SIN_MATCH,
            sample_id=sample_id,
            crudo=crudo,
            detalle="Tubo no encontrado",
            actor=actor,
        )
        return WorklistResult(
            estado=MensajeInstrumento.Estado.SIN_MATCH,
            sample_id=sample_id,
            interfaz=interfaz,
            detalle="Tubo no encontrado",
        )

    solicitud = muestra.solicitud
    if muestra.estado not in MUESTRA_ESTADOS_WORKLIST:
        detalle = f"Muestra en estado {muestra.estado}; no se envía worklist."
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=MensajeInstrumento.Estado.ERROR,
            sample_id=sample_id,
            crudo=crudo,
            detalle=detalle,
            muestra=muestra,
            solicitud=solicitud,
            actor=actor,
        )
        return WorklistResult(
            estado=MensajeInstrumento.Estado.ERROR,
            sample_id=sample_id,
            interfaz=interfaz,
            muestra=muestra,
            solicitud=solicitud,
            detalle=detalle,
        )

    if solicitud.estado not in ESTADOS_CARGABLES:
        detalle = f"Orden en estado {solicitud.estado}; no se envía worklist."
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=MensajeInstrumento.Estado.ERROR,
            sample_id=sample_id,
            crudo=crudo,
            detalle=detalle,
            muestra=muestra,
            solicitud=solicitud,
            actor=actor,
        )
        return WorklistResult(
            estado=MensajeInstrumento.Estado.ERROR,
            sample_id=sample_id,
            interfaz=interfaz,
            muestra=muestra,
            solicitud=solicitud,
            numero_solicitud=solicitud.numero or "",
            detalle=detalle,
        )

    try:
        verificar_iqc_para_solicitud(
            solicitud,
            actor=actor,
            permitir_override=False,
            equipo=interfaz.equipo,
        )
    except QcGateError as exc:
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=MensajeInstrumento.Estado.IQC_BLOQUEADO,
            sample_id=sample_id,
            crudo=crudo,
            detalle=str(exc)[:255],
            muestra=muestra,
            solicitud=solicitud,
            actor=actor,
        )
        return WorklistResult(
            estado=MensajeInstrumento.Estado.IQC_BLOQUEADO,
            sample_id=sample_id,
            interfaz=interfaz,
            muestra=muestra,
            solicitud=solicitud,
            numero_solicitud=solicitud.numero or "",
            detalle=str(exc),
        )

    mapeo_te = _mapeos_por_tipo_examen(interfaz)
    analitos: list[AnalitoWorklist] = []
    for r in _pendientes_tubo(muestra, interfaz):
        codigo_inst = mapeo_te.get(r.tipo_examen_id)
        if not codigo_inst:
            continue
        analitos.append(
            AnalitoWorklist(
                codigo_instrumento=codigo_inst,
                tipo_examen_codigo=r.tipo_examen.codigo,
                tipo_examen_id=r.tipo_examen_id,
                resultado_id=r.pk,
            )
        )

    pac = getattr(solicitud, "paciente", None)
    registrar_mensaje(
        interfaz=interfaz,
        direccion=MensajeInstrumento.Direccion.OUT,
        estado=MensajeInstrumento.Estado.OK,
        sample_id=sample_id,
        crudo=crudo,
        detalle=f"{len(analitos)} ensayos",
        muestra=muestra,
        solicitud=solicitud,
        actor=actor,
    )
    return WorklistResult(
        estado=MensajeInstrumento.Estado.OK,
        sample_id=sample_id,
        interfaz=interfaz,
        muestra=muestra,
        solicitud=solicitud,
        paciente_apellido=(getattr(pac, "apellido", None) or "")[:40],
        paciente_nombre=(getattr(pac, "nombre", None) or "")[:40],
        paciente_dni=(getattr(pac, "dni", None) or "")[:20],
        numero_solicitud=solicitud.numero or "",
        analitos=analitos,
    )


def _parse_valor_clinico(raw: Any) -> tuple[str, Decimal | None]:
    text = str(raw if raw is not None else "").strip()
    if not text:
        return "", None
    try:
        num = quantize_valor_numerico(Decimal(text.replace(",", ".")))
        return str(num), num
    except (InvalidOperation, ValueError, TypeError):
        return text, None


def ingestar_resultados(
    *,
    sample_id: str,
    interfaz: InterfazInstrumento,
    items: list[IngestaItem],
    actor=None,
    crudo: str = "",
) -> IngestaResult:
    interfaz.tocar()
    actor = _actor_db(actor)
    muestra = resolver_muestra_por_sample_id(sample_id)
    if muestra is None:
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=MensajeInstrumento.Estado.SIN_MATCH,
            sample_id=sample_id,
            crudo=crudo,
            detalle="Tubo no encontrado",
            actor=actor,
        )
        return IngestaResult(
            estado=MensajeInstrumento.Estado.SIN_MATCH,
            sample_id=sample_id,
            interfaz=interfaz,
            detalle="Tubo no encontrado",
        )

    solicitud = muestra.solicitud
    mapeos = _mapeos_activos(interfaz)
    pendientes = {r.tipo_examen_id: r for r in _pendientes_tubo(muestra, interfaz)}
    payload: list[dict[str, Any]] = []
    sin_match: list[str] = []

    for item in items:
        codigo = normalizar_codigo_analito(item.codigo_instrumento)
        mapeo = mapeos.get(codigo)
        if mapeo is None:
            sin_match.append(codigo or "?")
            continue
        resultado = pendientes.get(mapeo.tipo_examen_id)
        if resultado is None:
            sin_match.append(codigo)
            continue
        valor_txt, valor_num = _parse_valor_clinico(item.valor)
        if not valor_txt:
            sin_match.append(codigo)
            continue
        row: dict[str, Any] = {
            "id": resultado.pk,
            "valor": valor_txt,
            "muestra_id": muestra.pk,
        }
        if valor_num is not None:
            row["valor_numerico"] = valor_num
        if item.unidad:
            row["unidad"] = item.unidad
        payload.append(row)

    if not payload:
        estado = MensajeInstrumento.Estado.SIN_MATCH
        detalle = "Ningún analito coincide con la orden"
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=estado,
            sample_id=sample_id,
            crudo=crudo,
            detalle=detalle,
            muestra=muestra,
            solicitud=solicitud,
            actor=actor,
        )
        return IngestaResult(
            estado=estado,
            sample_id=sample_id,
            interfaz=interfaz,
            muestra=muestra,
            solicitud=solicitud,
            sin_match=sin_match,
            detalle=detalle,
        )

    try:
        with transaction.atomic():
            cargar_resultados_solicitud(
                solicitud_id=solicitud.pk,
                resultados_data=payload,
                actor=actor,
                informar_parcial=True,
                view="instrumentos.ingesta",
                equipo_iqc=interfaz.equipo,
                fuente="INSTRUMENTO",
            )
    except CargaResultadosError as exc:
        estado = (
            MensajeInstrumento.Estado.IQC_BLOQUEADO
            if getattr(exc, "code", "") == "iqc"
            else MensajeInstrumento.Estado.ERROR
        )
        registrar_mensaje(
            interfaz=interfaz,
            direccion=MensajeInstrumento.Direccion.IN,
            estado=estado,
            sample_id=sample_id,
            crudo=crudo,
            detalle=str(exc)[:255],
            muestra=muestra,
            solicitud=solicitud,
            actor=actor,
        )
        return IngestaResult(
            estado=estado,
            sample_id=sample_id,
            interfaz=interfaz,
            muestra=muestra,
            solicitud=solicitud,
            sin_match=sin_match,
            detalle=str(exc),
        )

    solicitud.refresh_from_db()
    detalle = f"Cargados {len(payload)}"
    if sin_match:
        detalle += f"; sin match {len(sin_match)}"
    registrar_mensaje(
        interfaz=interfaz,
        direccion=MensajeInstrumento.Direccion.IN,
        estado=MensajeInstrumento.Estado.OK,
        sample_id=sample_id,
        crudo=crudo,
        detalle=detalle[:255],
        muestra=muestra,
        solicitud=solicitud,
        actor=actor,
    )
    return IngestaResult(
        estado=MensajeInstrumento.Estado.OK,
        sample_id=sample_id,
        interfaz=interfaz,
        muestra=muestra,
        solicitud=solicitud,
        cargados=len(payload),
        sin_match=sin_match,
        detalle=detalle,
    )
