"""Estado administrativo de cobertura / obra social en órdenes LIMS."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from rest_framework import status
from rest_framework.response import Response


def obra_social_efectiva(obj: Any) -> tuple[str, str]:
    """OS y afiliado a mostrar: snapshot de la orden si hay, si no ficha paciente.

    Compatible con órdenes históricas sin ``obra_social_orden``.
    """
    snap_os = (getattr(obj, "obra_social_orden", None) or "").strip()
    snap_afil = (getattr(obj, "afiliado_orden", None) or "").strip()
    if snap_os:
        return snap_os, snap_afil
    paciente = getattr(obj, "paciente", None)
    if paciente is None:
        return "", ""
    from pacientes.obras_sociales import label_obra_social

    os_raw = getattr(paciente, "obra_social", None)
    return (
        label_obra_social(os_raw),
        (getattr(paciente, "numero_afiliado", None) or "").strip(),
    )

ESTADO_OBRA_SOCIAL_CHOICES = [
    ("AUTORIZADO", "Autorizado"),
    ("DEBE_ORDEN", "Debe orden"),
    ("FALTA_AUTORIZACION", "Falta autorización"),
    ("DEBE_ABONAR", "Debe abonar"),
]

ESTADOS_OBRA_SOCIAL_VALIDOS = frozenset(code for code, _label in ESTADO_OBRA_SOCIAL_CHOICES)

# Valores aceptados para dejar el estado sin cargar.
_VACIOS = frozenset({"", "SIN_CARGAR", "NONE", "NULL"})

MENSAJE_NO_AUTORIZADA = (
    "No se puede validar ni emitir el informe: la obra social de esta orden "
    "ambulatoria no está autorizada. Cargá el estado «Autorizado» en Obra social."
)


def origen_requiere_autorizacion_obra_social(origen: str | None) -> bool:
    """Ambulatorio (consultorio y receta externa). Internación y guardia no exigen este paso."""
    from laboratorio.origen_solicitud import (
        AMBULATORIO_CEHTA,
        AMBULATORIO_ICPL,
        EXTERNO_CEHTA,
        EXTERNO_ICPL,
    )

    return (origen or "") in {
        AMBULATORIO_CEHTA,
        AMBULATORIO_ICPL,
        EXTERNO_CEHTA,
        EXTERNO_ICPL,
    }


def obra_social_permite_liberar(solicitud) -> bool:
    if not origen_requiere_autorizacion_obra_social(getattr(solicitud, "origen_solicitud", None)):
        return True
    return (getattr(solicitud, "estado_obra_social", None) or "") == "AUTORIZADO"


def parse_estado_obra_social(value: object) -> str:
    """Normaliza el código; cadena vacía = sin cargar. Lanza ValueError si es inválido."""
    if value is None:
        return ""
    codigo = str(value).strip().upper()
    if codigo in _VACIOS:
        return ""
    if codigo not in ESTADOS_OBRA_SOCIAL_VALIDOS:
        opciones = ", ".join(sorted(ESTADOS_OBRA_SOCIAL_VALIDOS))
        raise ValueError(
            f"estado_obra_social inválido. Use uno de: {opciones}, o vacío para sin cargar."
        )
    return codigo


def parse_monto_debe_abonar(value: object) -> Decimal | None:
    """Normaliza el monto opcional. Vacío/null → None. Lanza ValueError si es inválido."""
    if value is None:
        return None
    if isinstance(value, str):
        texto = value.strip().replace(",", ".")
        if not texto or texto.upper() in _VACIOS:
            return None
        value = texto
    if isinstance(value, bool):
        raise ValueError("monto_debe_abonar inválido.")
    try:
        monto = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("monto_debe_abonar inválido.") from exc
    if monto < 0:
        raise ValueError("monto_debe_abonar no puede ser negativo.")
    return monto.quantize(Decimal("0.01"))


def guardar_estado_obra_social(
    instance,
    raw_value,
    *,
    actor,
    view_name: str,
    raw_monto=None,
):
    """Persiste estado (y monto opcional si DEBE_ABONAR) y audita. Devuelve Response 400 o None."""
    from auditoria.audit_service import log_update
    from auditoria.snapshot import safe_model_snapshot

    try:
        nuevo = parse_estado_obra_social(raw_value)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if nuevo == "DEBE_ABONAR":
        try:
            nuevo_monto = parse_monto_debe_abonar(raw_monto)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    else:
        nuevo_monto = None

    before = safe_model_snapshot(instance)
    changed = False
    if instance.estado_obra_social != nuevo:
        instance.estado_obra_social = nuevo
        changed = True
    actual_monto = getattr(instance, "monto_debe_abonar", None)
    if actual_monto != nuevo_monto:
        instance.monto_debe_abonar = nuevo_monto
        changed = True

    if changed:
        instance.save(update_fields=["estado_obra_social", "monto_debe_abonar"])
        log_update(
            actor=actor,
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "action": "estado_obra_social",
                "view": view_name,
                "estado_obra_social": nuevo,
                "monto_debe_abonar": str(nuevo_monto) if nuevo_monto is not None else None,
            },
        )
    return None
