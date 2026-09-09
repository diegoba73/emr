"""
Servicio de etiqueta física de Muestra (40×23 mm / ZPL).

Flujo: Muestra persistida → datos seguros → 4 líneas → ZPL (perfil) → transporte.

Imprimir NO marca TOMADA ni pasa la orden a EN_PROCESO: el tubo sigue
PENDIENTE_TOMA hasta la recepción.

Validar orden: ver ``MUESTRA_ESTADOS_PENDIENTES_RECEPCION`` /
``_validar_muestras_para_cierre`` — tubos PENDIENTE_TOMA/TOMADA bloquean listo/validar
hasta recepcionarlos o cancelarlos; la carga de resultados del tubo recibido sí está permitida.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from laboratorio.label_printer_transport import (
    LabelPrinterError,
    get_label_printer_config,
    send_zpl_to_network_printer,
)
from laboratorio.label_profiles import get_label_profile
from laboratorio.label_zpl import (
    CodigoBarraZplError,
    build_label_lines,
    escape_zpl_fd,
    normalize_lugar_extraccion,
    prepare_codigo_barra_for_zpl,
    render_zpl_40x23,
)
from laboratorio.models_catalog import Muestra


class EtiquetaMuestraError(ValueError):
    """Datos insuficientes o inconsistentes para etiqueta definitiva."""


@dataclass(frozen=True)
class EtiquetaMuestraPayload:
    muestra_id: int
    profile: str
    width_mm: int
    height_mm: int
    lines: list[str]
    zpl: str
    printable: bool
    validation_errors: list[str]


def tipo_operacional_imprimible(muestra: Muestra) -> str:
    """
    Texto de la 4.ª línea (tubo/anticoagulante operativo).

    En el dominio real, EDTA vive en ``TipoContenedor`` (código/aditivo),
    mientras ``TipoMuestra`` es material (p.ej. SANGRE_EDTA / sangre).
    Preferimos aditivo corto del contenedor; si no, código del contenedor;
    si no hay contenedor, código del tipo de muestra.
    """
    tc = getattr(muestra, "tipo_contenedor", None)
    if tc is not None:
        aditivo = (getattr(tc, "aditivo", None) or "").strip()
        if aditivo:
            # "EDTA K2" → preferir token corto legible en 40 mm.
            upper = aditivo.upper()
            if "EDTA" in upper:
                return "EDTA"
            # Evitar "SIN ADITIVO" verboso: usar código del tubo.
            if upper.startswith("SIN "):
                codigo = (tc.codigo or "").strip()
                return codigo or aditivo
            # Primer token significativo (p.ej. "Citrato de sodio" → CITRATO).
            token = aditivo.split()[0].strip(" ,.;")
            return token.upper() if token else (tc.codigo or "").strip()
        codigo = (tc.codigo or "").strip()
        if codigo:
            return codigo
    tm = getattr(muestra, "tipo_muestra", None)
    if tm is not None:
        codigo = (getattr(tm, "codigo", None) or "").strip()
        if codigo:
            return codigo
        return (getattr(tm, "nombre", None) or "").strip()
    return ""


def resolver_lugar_etiqueta_desde_solicitud(solicitud) -> str:
    """
    Lugar para etiqueta cuando la muestra aún no tiene snapshot.
    Preferir procedencia (sector/cama); fallback label de origen_solicitud.
    """
    if solicitud is None:
        return ""
    from laboratorio.origen_solicitud import label_origen_solicitud
    from laboratorio.procedencia_display import resolver_procedencia_solicitud

    proc = resolver_procedencia_solicitud(solicitud)
    detalle = (proc.get("procedencia_display") or "").strip()
    origen_label = label_origen_solicitud(getattr(solicitud, "origen_solicitud", None) or "")
    if detalle and detalle not in ("—", "-"):
        # Si el detalle es más específico que el título de origen, usarlo.
        return detalle
    if origen_label and origen_label != "—":
        return origen_label
    return detalle if detalle != "—" else ""


def _lugar_efectivo_etiqueta(muestra: Muestra) -> str:
    lugar = (getattr(muestra, "lugar_extraccion", None) or "").strip()
    if lugar:
        return lugar
    sol = getattr(muestra, "solicitud", None)
    return resolver_lugar_etiqueta_desde_solicitud(sol)


def _fecha_efectiva_etiqueta(muestra: Muestra, *, preview_now_if_missing: bool):
    if muestra.fecha_toma is not None:
        return muestra.fecha_toma
    if preview_now_if_missing:
        return timezone.now()
    return None


def _collect_validation_errors(
    muestra: Muestra,
    *,
    lugar_efectivo: str,
    fecha_efectiva,
) -> list[str]:
    """
    1) Identidad codigo_barra exacta (sin strip).
    2) Resto de campos (lugar/fecha pueden venir resueltos para preview/print).
    3) Revalidar obligatorios tras sanitización display.
    """
    errors: list[str] = []
    if muestra.paciente_id and muestra.solicitud_id:
        if muestra.paciente_id != muestra.solicitud.paciente_id:
            errors.append("El paciente de la muestra no coincide con el de la solicitud.")

    # Identidad: string ORIGINAL, sin strip previo.
    raw_codigo = muestra.codigo_barra
    if raw_codigo is None or raw_codigo == "":
        errors.append("La muestra no tiene código de barras asignado.")
    else:
        try:
            prepare_codigo_barra_for_zpl(raw_codigo)
        except CodigoBarraZplError as exc:
            errors.append(str(exc))

    pac = muestra.paciente
    apellido_raw = (getattr(pac, "apellido", None) or "") if pac else ""
    dni_raw = (getattr(pac, "dni", None) or "") if pac else ""
    if not str(apellido_raw).strip():
        errors.append("El paciente no tiene apellido registrado; no se puede imprimir la etiqueta.")
    if not str(dni_raw).strip():
        errors.append("El paciente no tiene DNI registrado; no se puede imprimir la etiqueta.")
    if fecha_efectiva is None:
        errors.append("Falta registrar la toma de la muestra (fecha/hora de extracción).")

    lugar_raw = lugar_efectivo or ""
    if not str(lugar_raw).strip():
        errors.append(
            "Falta el lugar de extracción (origen/procedencia de la orden no disponible)."
        )

    tipo_raw = tipo_operacional_imprimible(muestra)
    if not str(tipo_raw).strip():
        errors.append("No hay tipo de tubo/muestra imprimible asociado.")

    # Tras sanitización: obligatorios display no pueden quedar vacíos.
    if str(apellido_raw).strip():
        if not escape_zpl_fd(apellido_raw):
            errors.append(
                "El apellido del paciente no es representable en la etiqueta."
            )
    if str(dni_raw).strip():
        if not escape_zpl_fd(re.sub(r"\s+", "", str(dni_raw))):
            errors.append("El DNI del paciente no es representable en la etiqueta.")
    if str(lugar_raw).strip():
        if not escape_zpl_fd(normalize_lugar_extraccion(str(lugar_raw))):
            errors.append(
                "El lugar de extracción no es representable en la etiqueta."
            )
    if str(tipo_raw).strip():
        if not escape_zpl_fd(str(tipo_raw)):
            errors.append("El tipo de tubo/muestra no es representable en la etiqueta.")

    return errors


def build_etiqueta_muestra(
    muestra: Muestra,
    *,
    profile_key: str | None = None,
    require_printable: bool = False,
    preview_now_if_missing_fecha: bool = True,
) -> EtiquetaMuestraPayload:
    cfg = get_label_printer_config()
    profile = get_label_profile(profile_key or cfg.profile_key)
    lugar_eff = _lugar_efectivo_etiqueta(muestra)
    fecha_eff = _fecha_efectiva_etiqueta(
        muestra, preview_now_if_missing=preview_now_if_missing_fecha
    )
    errors = _collect_validation_errors(
        muestra, lugar_efectivo=lugar_eff, fecha_efectiva=fecha_eff
    )
    printable = len(errors) == 0

    if require_printable and not printable:
        raise EtiquetaMuestraError(errors[0])

    lines: list[str] = []
    zpl = ""
    if printable:
        pac = muestra.paciente
        try:
            label_lines = build_label_lines(
                codigo_barra=muestra.codigo_barra if muestra.codigo_barra is not None else "",
                apellido=getattr(pac, "apellido", None),
                nombre=getattr(pac, "nombre", None),
                dni=getattr(pac, "dni", None),
                lugar_extraccion=lugar_eff,
                fecha_toma=fecha_eff,
                tipo_operacional=tipo_operacional_imprimible(muestra),
            )
        except CodigoBarraZplError as exc:
            # Defensa: no generar ZPL con identidad alterada.
            err = str(exc)
            if require_printable:
                raise EtiquetaMuestraError(err) from exc
            return EtiquetaMuestraPayload(
                muestra_id=muestra.pk,
                profile=profile.key,
                width_mm=profile.width_mm,
                height_mm=profile.height_mm,
                lines=[],
                zpl="",
                printable=False,
                validation_errors=[*errors, err],
            )
        lines = label_lines.as_list()
        rendered = render_zpl_40x23(label_lines, profile)
        zpl = rendered.zpl
        # Preview y ZPL deben coincidir carácter a carácter en ^FD.
        for expected, lay in zip(lines, rendered.layouts, strict=True):
            if expected != lay.text:
                raise EtiquetaMuestraError(
                    "Inconsistencia entre líneas de preview y contenido ZPL."
                )
            if f"^FD{lay.text}^FS" not in zpl:
                raise EtiquetaMuestraError(
                    "Inconsistencia entre líneas de preview y contenido ZPL."
                )
        if f"^PW{profile.width_dots}" not in zpl or f"^LL{profile.height_dots}" not in zpl:
            raise EtiquetaMuestraError("ZPL generado fuera del perfil esperado.")
        if not rendered.all_fit_width():
            raise EtiquetaMuestraError("ZPL generado fuera del ancho útil del perfil.")

    return EtiquetaMuestraPayload(
        muestra_id=muestra.pk,
        profile=profile.key,
        width_mm=profile.width_mm,
        height_mm=profile.height_mm,
        lines=lines,
        zpl=zpl,
        printable=printable,
        validation_errors=errors,
    )


def etiqueta_payload_to_dict(payload: EtiquetaMuestraPayload) -> dict[str, Any]:
    return {
        "muestra_id": payload.muestra_id,
        "profile": payload.profile,
        "width_mm": payload.width_mm,
        "height_mm": payload.height_mm,
        "lines": payload.lines,
        "zpl": payload.zpl,
        "printable": payload.printable,
        "validation_errors": payload.validation_errors,
    }


def audit_metadata_etiqueta_print(
    muestra: Muestra,
    *,
    profile_key: str,
    resultado: str,
    transport: str,
    view: str,
) -> dict[str, Any]:
    """Metadata segura: sin PHI, código de barras, ZPL ni lugar de extracción."""
    return {
        "accion": "muestra_etiqueta_print",
        "muestra_id": muestra.pk,
        "solicitud_id": muestra.solicitud_id,
        "perfil_impresora": profile_key,
        "resultado": resultado,
        "transport": transport,
        "view": view,
    }


def _persistir_snapshot_etiqueta_sin_fsm(muestra: Muestra) -> Muestra:
    """
    Completa lugar (desde origen) y fecha_toma=now si faltan, sin cambiar estado
    ni coordinar la solicitud a EN_PROCESO.
    """
    update_fields: list[str] = []
    with transaction.atomic():
        locked = (
            Muestra.objects.select_for_update()
            .select_related("solicitud", "paciente", "tipo_contenedor", "tipo_muestra")
            .get(pk=muestra.pk)
        )
        if not (locked.lugar_extraccion or "").strip():
            lugar = resolver_lugar_etiqueta_desde_solicitud(locked.solicitud)
            if lugar:
                locked.lugar_extraccion = normalize_lugar_extraccion(lugar)
                update_fields.append("lugar_extraccion")
        if locked.fecha_toma is None:
            locked.fecha_toma = timezone.now()
            update_fields.append("fecha_toma")
        if update_fields:
            if hasattr(locked, "updated_at"):
                locked.updated_at = timezone.now()
                update_fields.append("updated_at")
            locked.save(update_fields=update_fields)
        return locked


def imprimir_etiqueta_muestra(
    muestra: Muestra,
    *,
    actor=None,
    view: str = "MuestraTransaccionalViewSet.imprimir_etiqueta",
) -> dict[str, Any]:
    """
    Completa snapshot de etiqueta si falta (lugar/fecha), genera ZPL, envía y audita.

    No muta estado de la muestra ni de la solicitud (sigue pendiente de recepción).
    No reintenta el envío.
    """
    from auditoria.audit_service import log_event

    muestra = _persistir_snapshot_etiqueta_sin_fsm(muestra)
    payload = build_etiqueta_muestra(
        muestra, require_printable=True, preview_now_if_missing_fecha=False
    )
    cfg = get_label_printer_config()

    try:
        send_zpl_to_network_printer(payload.zpl, config=cfg)
    except LabelPrinterError:
        # Sin evento de éxito; el caller traduce a HTTP.
        raise

    log_event(
        action="UPDATE",
        actor=actor,
        entity=muestra,
        before=None,
        after=None,
        module="laboratorio",
        metadata=audit_metadata_etiqueta_print(
            muestra,
            profile_key=payload.profile,
            resultado="ok",
            transport="network_socket",
            view=view,
        ),
        success=True,
    )
    return {
        "muestra_id": muestra.pk,
        "profile": payload.profile,
        "resultado": "ok",
        "printer_enabled": True,
    }
