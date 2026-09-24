"""
Servicio de etiqueta física de EstudioMicrobiologia (40×23 mm / ZPL).

Mismo perfil y layout que muestras de lab clínico. El servidor no habla con
la impresora: el navegador envía el ZPL al agente USB local.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from laboratorio.label_profiles import get_label_profile
from laboratorio.label_zpl import (
    CodigoBarraZplError,
    build_label_lines,
    escape_zpl_fd,
    normalize_lugar_extraccion,
    prepare_codigo_barra_for_zpl,
    render_zpl_40x23,
)
from laboratorio.microbiologia_estado import MicrobiologiaAccionError, imprimir_etiquetas_estudios
from laboratorio.models_microbiologia import EstudioMicrobiologia
from laboratorio.origen_solicitud import label_origen_solicitud
from laboratorio.services_etiqueta_muestra import resolver_lugar_etiqueta_desde_solicitud


class EtiquetaMicroError(ValueError):
    """Datos insuficientes o inconsistentes para etiqueta definitiva."""


@dataclass(frozen=True)
class EtiquetaMicroPayload:
    estudio_id: int
    profile: str
    width_mm: int
    height_mm: int
    lines: list[str]
    zpl: str
    printable: bool
    validation_errors: list[str]


def tipo_operacional_imprimible_micro(estudio: EstudioMicrobiologia) -> str:
    """Línea 4: código de cultivo (corto); fallback tipo_estudio / muestra micro."""
    tc = getattr(estudio, "tipo_cultivo", None)
    if tc is not None:
        codigo = (getattr(tc, "codigo", None) or "").strip()
        if codigo:
            return codigo
        nombre = (getattr(tc, "nombre", None) or "").strip()
        if nombre:
            return nombre
    tipo_estudio = (getattr(estudio, "tipo_estudio", None) or "").strip()
    if tipo_estudio:
        return tipo_estudio
    tm = getattr(estudio, "tipo_muestra_micro", None)
    if tm is not None:
        codigo = (getattr(tm, "codigo", None) or "").strip()
        if codigo:
            return codigo
        return (getattr(tm, "nombre", None) or "").strip()
    return ""


def resolver_lugar_etiqueta_estudio(estudio: EstudioMicrobiologia) -> str:
    """Lugar desde solicitud LIMS vinculada o label de origen_solicitud del estudio."""
    sol = getattr(estudio, "solicitud", None)
    if sol is not None:
        lugar = resolver_lugar_etiqueta_desde_solicitud(sol)
        if lugar:
            return lugar
    origen = getattr(estudio, "origen_solicitud", None) or ""
    label = label_origen_solicitud(origen)
    if label and label != "—":
        return label
    return ""


def _codigo_efectivo(estudio: EstudioMicrobiologia) -> str:
    raw = getattr(estudio, "codigo_barra", None)
    if raw:
        return raw
    return (getattr(estudio, "numero", None) or "") or ""


def _fecha_efectiva_etiqueta(
    estudio: EstudioMicrobiologia,
    *,
    preview_now_if_missing: bool,
):
    if estudio.etiquetas_impresas_at is not None:
        return estudio.etiquetas_impresas_at
    if preview_now_if_missing:
        return timezone.now()
    return None


def _collect_validation_errors(
    estudio: EstudioMicrobiologia,
    *,
    lugar_efectivo: str,
    fecha_efectiva,
    codigo_efectivo: str,
) -> list[str]:
    errors: list[str] = []

    if codigo_efectivo is None or codigo_efectivo == "":
        errors.append("El estudio no tiene código de barras ni número de protocolo.")
    else:
        try:
            prepare_codigo_barra_for_zpl(codigo_efectivo)
        except CodigoBarraZplError as exc:
            errors.append(str(exc))

    pac = estudio.paciente
    apellido_raw = (getattr(pac, "apellido", None) or "") if pac else ""
    dni_raw = (getattr(pac, "dni", None) or "") if pac else ""
    if not str(apellido_raw).strip():
        errors.append("El paciente no tiene apellido registrado; no se puede imprimir la etiqueta.")
    if not str(dni_raw).strip():
        errors.append("El paciente no tiene DNI registrado; no se puede imprimir la etiqueta.")
    if fecha_efectiva is None:
        errors.append("Falta la fecha/hora de impresión de la etiqueta.")

    lugar_raw = lugar_efectivo or ""
    if not str(lugar_raw).strip():
        errors.append(
            "Falta el lugar (origen/procedencia del pedido no disponible)."
        )

    tipo_raw = tipo_operacional_imprimible_micro(estudio)
    if not str(tipo_raw).strip():
        errors.append("No hay tipo de cultivo/muestra imprimible asociado.")

    if str(apellido_raw).strip() and not escape_zpl_fd(apellido_raw):
        errors.append("El apellido del paciente no es representable en la etiqueta.")
    if str(dni_raw).strip() and not escape_zpl_fd(re.sub(r"\s+", "", str(dni_raw))):
        errors.append("El DNI del paciente no es representable en la etiqueta.")
    if str(lugar_raw).strip() and not escape_zpl_fd(normalize_lugar_extraccion(str(lugar_raw))):
        errors.append("El lugar no es representable en la etiqueta.")
    if str(tipo_raw).strip() and not escape_zpl_fd(str(tipo_raw)):
        errors.append("El tipo de cultivo/muestra no es representable en la etiqueta.")

    return errors


def build_etiqueta_estudio_micro(
    estudio: EstudioMicrobiologia,
    *,
    profile_key: str | None = None,
    require_printable: bool = False,
    preview_now_if_missing_fecha: bool = True,
) -> EtiquetaMicroPayload:
    profile = get_label_profile(profile_key)
    lugar_eff = resolver_lugar_etiqueta_estudio(estudio)
    fecha_eff = _fecha_efectiva_etiqueta(
        estudio, preview_now_if_missing=preview_now_if_missing_fecha
    )
    codigo_eff = _codigo_efectivo(estudio)
    errors = _collect_validation_errors(
        estudio,
        lugar_efectivo=lugar_eff,
        fecha_efectiva=fecha_eff,
        codigo_efectivo=codigo_eff,
    )
    printable = len(errors) == 0

    if require_printable and not printable:
        raise EtiquetaMicroError(errors[0])

    lines: list[str] = []
    zpl = ""
    if printable:
        pac = estudio.paciente
        try:
            label_lines = build_label_lines(
                codigo_barra=codigo_eff,
                apellido=getattr(pac, "apellido", None),
                nombre=getattr(pac, "nombre", None),
                dni=getattr(pac, "dni", None),
                lugar_extraccion=lugar_eff,
                fecha_toma=fecha_eff,
                tipo_operacional=tipo_operacional_imprimible_micro(estudio),
            )
        except CodigoBarraZplError as exc:
            err = str(exc)
            if require_printable:
                raise EtiquetaMicroError(err) from exc
            return EtiquetaMicroPayload(
                estudio_id=estudio.pk,
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
        for expected, lay in zip(lines, rendered.layouts, strict=True):
            if expected != lay.text:
                raise EtiquetaMicroError(
                    "Inconsistencia entre líneas de preview y contenido ZPL."
                )
            if f"^FD{lay.text}^FS" not in zpl:
                raise EtiquetaMicroError(
                    "Inconsistencia entre líneas de preview y contenido ZPL."
                )
        if f"^PW{profile.width_dots}" not in zpl or f"^LL{profile.height_dots}" not in zpl:
            raise EtiquetaMicroError("ZPL generado fuera del perfil esperado.")
        if not rendered.all_fit_width():
            raise EtiquetaMicroError("ZPL generado fuera del ancho útil del perfil.")

    return EtiquetaMicroPayload(
        estudio_id=estudio.pk,
        profile=profile.key,
        width_mm=profile.width_mm,
        height_mm=profile.height_mm,
        lines=lines,
        zpl=zpl,
        printable=printable,
        validation_errors=errors,
    )


def etiqueta_micro_payload_to_dict(payload: EtiquetaMicroPayload) -> dict[str, Any]:
    return {
        "estudio_id": payload.estudio_id,
        "profile": payload.profile,
        "width_mm": payload.width_mm,
        "height_mm": payload.height_mm,
        "lines": payload.lines,
        "zpl": payload.zpl,
        "printable": payload.printable,
        "validation_errors": payload.validation_errors,
    }


def audit_metadata_etiqueta_print_micro(
    estudio: EstudioMicrobiologia,
    *,
    profile_key: str,
    resultado: str,
    transport: str,
    view: str,
) -> dict[str, Any]:
    """Metadata segura: sin PHI, código de barras, ZPL ni lugar."""
    return {
        "accion": "micro_etiqueta_print",
        "estudio_id": estudio.pk,
        "perfil_impresora": profile_key,
        "resultado": resultado,
        "transport": transport,
        "view": view,
    }


def imprimir_etiqueta_estudio_micro(
    estudio: EstudioMicrobiologia,
    *,
    actor=None,
    view: str = "EstudioMicrobiologiaViewSet.imprimir_etiqueta",
) -> dict[str, Any]:
    """
    Asigna barcode / etiquetas_impresas_at (PENDIENTE) y devuelve ZPL.

    No envía a impresora. No audita éxito: llamar confirmar tras el agente local.
    """
    try:
        preparados = imprimir_etiquetas_estudios(
            [estudio.pk],
            actor=actor,
            view=view,
        )
    except MicrobiologiaAccionError as exc:
        raise EtiquetaMicroError(str(exc)) from exc
    estudio = preparados[0]
    # Recargar FKs usados en líneas.
    estudio = (
        EstudioMicrobiologia.objects.select_related(
            "paciente",
            "tipo_cultivo",
            "tipo_muestra_micro",
            "solicitud",
        ).get(pk=estudio.pk)
    )
    payload = build_etiqueta_estudio_micro(
        estudio, require_printable=True, preview_now_if_missing_fecha=False
    )
    return {
        "estudio_id": estudio.pk,
        "profile": payload.profile,
        "resultado": "prepared",
        "zpl": payload.zpl,
    }


def confirmar_impresion_etiqueta_estudio_micro(
    estudio: EstudioMicrobiologia,
    *,
    actor=None,
    view: str = "EstudioMicrobiologiaViewSet.confirmar_impresion_etiqueta",
    profile_key: str | None = None,
) -> dict[str, Any]:
    """Audita impresión local OK. Sin PHI/ZPL. No muta estado del estudio."""
    from auditoria.audit_service import log_event

    profile = (profile_key or "").strip() or get_label_profile().key
    log_event(
        action="UPDATE",
        actor=actor,
        entity=estudio,
        before=None,
        after=None,
        module="laboratorio",
        metadata=audit_metadata_etiqueta_print_micro(
            estudio,
            profile_key=profile,
            resultado="ok",
            transport="local_agent",
            view=view,
        ),
        success=True,
    )
    return {
        "estudio_id": estudio.pk,
        "profile": profile,
        "resultado": "ok",
        "transport": "local_agent",
    }
