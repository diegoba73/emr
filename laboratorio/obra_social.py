"""Estado administrativo de cobertura / obra social en órdenes LIMS."""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

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


def guardar_estado_obra_social(instance, raw_value, *, actor, view_name: str):
    """Persiste el estado y audita. Devuelve Response 400 o None si ok."""
    from auditoria.audit_service import log_update
    from auditoria.snapshot import safe_model_snapshot

    try:
        nuevo = parse_estado_obra_social(raw_value)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    before = safe_model_snapshot(instance)
    if instance.estado_obra_social != nuevo:
        instance.estado_obra_social = nuevo
        instance.save(update_fields=["estado_obra_social"])
        log_update(
            actor=actor,
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "action": "estado_obra_social",
                "view": view_name,
                "estado_obra_social": nuevo,
            },
        )
    return None
