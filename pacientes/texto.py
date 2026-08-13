"""Normalización de texto demográfico de ``Paciente`` (siempre mayúsculas)."""
from __future__ import annotations

from typing import Any

# Solo datos identificatorios / contacto escrito. No incluye email (técnico),
# teléfono (dígitos), DNI, ni resultados de laboratorio.
CAMPOS_PACIENTE_MAYUSCULAS: tuple[str, ...] = (
    "nombre",
    "apellido",
    "direccion",
    "obra_social",
    "numero_afiliado",
)


def normalizar_texto_paciente(value: Any) -> Any:
    """``strip`` + mayúsculas. Vacío → cadena vacía. ``None`` se preserva."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return ""
    return text.upper()


def aplicar_mayusculas_paciente(obj: Any) -> list[str]:
    """Aplica mayúsculas in-place. Devuelve nombres de campos modificados."""
    dirty: list[str] = []
    for field in CAMPOS_PACIENTE_MAYUSCULAS:
        if not hasattr(obj, field):
            continue
        raw = getattr(obj, field)
        if raw is None:
            continue
        nuevo = normalizar_texto_paciente(raw)
        if nuevo != raw:
            setattr(obj, field, nuevo)
            dirty.append(field)
    return dirty


def mayusculas_en_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Copia del dict con campos demográficos en mayúsculas (para bulk_create)."""
    out = dict(data)
    for field in CAMPOS_PACIENTE_MAYUSCULAS:
        if field in out and out[field] is not None:
            out[field] = normalizar_texto_paciente(out[field])
    return out
