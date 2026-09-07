"""
Servicio de etiqueta física de Muestra (40×23 mm / ZPL).

Flujo: Muestra persistida → datos seguros → 4 líneas → ZPL (perfil) → transporte.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

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


def _collect_validation_errors(muestra: Muestra) -> list[str]:
    """
    1) Identidad codigo_barra exacta (sin strip).
    2) Resto de campos.
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
    if not muestra.fecha_toma:
        errors.append("Falta registrar la toma de la muestra (fecha/hora de extracción).")

    lugar_raw = getattr(muestra, "lugar_extraccion", None) or ""
    if not str(lugar_raw).strip():
        errors.append("Falta el lugar de extracción de la muestra.")

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
) -> EtiquetaMuestraPayload:
    cfg = get_label_printer_config()
    profile = get_label_profile(profile_key or cfg.profile_key)
    errors = _collect_validation_errors(muestra)
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
                lugar_extraccion=muestra.lugar_extraccion or "",
                fecha_toma=muestra.fecha_toma,
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


def imprimir_etiqueta_muestra(
    muestra: Muestra,
    *,
    actor=None,
    view: str = "MuestraTransaccionalViewSet.imprimir_etiqueta",
) -> dict[str, Any]:
    """
    Valida, genera ZPL server-side, envía al transporte y audita éxito.

    No muta estado ni datos clínicos de la muestra.
    No reintenta el envío.
    """
    from auditoria.audit_service import log_event

    payload = build_etiqueta_muestra(muestra, require_printable=True)
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
