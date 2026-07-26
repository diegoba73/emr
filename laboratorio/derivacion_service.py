"""Helpers de derivación externa (LAC / IACA)."""
from __future__ import annotations

from laboratorio.models_derivacion import EstadoDerivacion, LaboratorioDerivacion


def defaults_derivacion_para_tipo(tipo_examen) -> dict:
    """Valores iniciales de derivación al crear un ResultadoExamen."""
    lab = getattr(tipo_examen, "laboratorio_derivacion", None)
    if lab is None and getattr(tipo_examen, "laboratorio_derivacion_id", None):
        lab = LaboratorioDerivacion.objects.filter(
            pk=tipo_examen.laboratorio_derivacion_id
        ).first()
    if lab and getattr(lab, "activo", True):
        return {
            "laboratorio_derivacion": lab,
            "estado_derivacion": EstadoDerivacion.PENDIENTE_ENVIO,
        }
    return {
        "laboratorio_derivacion": None,
        "estado_derivacion": EstadoDerivacion.LOCAL,
    }


def asegurar_labs_derivacion() -> tuple[LaboratorioDerivacion, LaboratorioDerivacion]:
    lac, _ = LaboratorioDerivacion.objects.get_or_create(
        codigo="LAC",
        defaults={
            "nombre": "LAC",
            "ciudad": "Trelew",
            "acepta_sangre": True,
            "acepta_orina": True,
            "acepta_cultivo": True,
            "acepta_cualquier": False,
            "activo": True,
        },
    )
    iaca, _ = LaboratorioDerivacion.objects.get_or_create(
        codigo="IACA",
        defaults={
            "nombre": "IACA",
            "ciudad": "Bahía Blanca",
            "acepta_sangre": True,
            "acepta_orina": True,
            "acepta_cultivo": True,
            "acepta_cualquier": True,
            "activo": True,
        },
    )
    return lac, iaca


# Códigos de pedido micro alineados a EstudioMicrobiologia.TIPO_ESTUDIO_CHOICES
MICRO_PEDIDO_CODIGOS = (
    "UROCULTIVO",
    "HEMOCULTIVO",
    "COPROCULTIVO",
    "CULTIVO_HERIDA",
    "CULTIVO_RUTINA",
    "HISOPADO",
    "PUNCION",
)
