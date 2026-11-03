"""Reglas de eliminación física de pacientes (solo admin / duplicados sin historia)."""
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist

from .models import Paciente

# Relaciones clínicas / operativas que impiden borrar (CASCADE o PROTECT).
# Las afiliaciones (PacienteAfiliacion) sí se borran con la ficha: son demografía.
_ACCESORES_BLOQUEO: tuple[tuple[str, str], ...] = (
    ("atenciones", "atenciones"),
    ("turnos", "turnos"),
    ("solicitudes_examen", "órdenes de laboratorio"),
    ("muestras_lims", "muestras LIMS"),
    ("estudios_microbiologia", "estudios de microbiología"),
    ("historiaclinica", "historia clínica"),
    ("internaciones", "internaciones"),
    ("internaciones_camas", "internaciones (camas)"),
    ("archivos", "archivos médicos"),
    ("solicitudes", "solicitudes"),
    ("estudios_complementarios", "estudios complementarios"),
    ("llegadas_recepcion", "llegadas en recepción"),
)


def bloqueos_eliminacion_paciente(paciente: Paciente) -> list[str]:
    """Devuelve etiquetas de relaciones que impiden el DELETE físico."""
    bloqueos: list[str] = []
    for accessor, label in _ACCESORES_BLOQUEO:
        if not hasattr(Paciente, accessor):
            continue
        try:
            related = getattr(paciente, accessor)
        except ObjectDoesNotExist:
            continue
        if related is None:
            continue
        if hasattr(related, "exists"):
            if related.exists():
                bloqueos.append(label)
        else:
            # OneToOne ya resuelto (p. ej. historiaclinica).
            bloqueos.append(label)
    return bloqueos
