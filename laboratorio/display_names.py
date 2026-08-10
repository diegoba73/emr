"""
Formato unificado de nombres para listados LIMS (Lab. Clínico + Microbiología).

Convención EMR: «Apellido, Nombre»; médicos internos: «Dr. Apellido, Nombre».
"""
from __future__ import annotations

import re
from typing import Any

_TITULO_MEDICO = re.compile(r"^(?:Dr\.?|Dra\.?)\s+", re.IGNORECASE)


def _apellido_nombre_parts(obj: Any) -> tuple[str, str]:
    apellido = (getattr(obj, "apellido", None) or "").strip()
    nombre = (getattr(obj, "nombre", None) or "").strip()
    return apellido, nombre


def format_apellido_nombre(persona: Any | None, *, fallback: str | None = None) -> str | None:
    """
    «Apellido, Nombre». Si falta alguno, devuelve el que haya.
    """
    if persona is None:
        return fallback
    apellido, nombre = _apellido_nombre_parts(persona)
    if apellido and nombre:
        return f"{apellido}, {nombre}"
    if apellido or nombre:
        return apellido or nombre
    if fallback is not None:
        return fallback
    return getattr(persona, "nombre_completo", None) or str(persona)


def format_medico_display(
    medico: Any | None = None,
    *,
    externo_nombre: str | None = None,
    fallback: str | None = "Sin médico asignado",
    prefix_dr: bool = True,
) -> str | None:
    """
    Médico interno: «Dr. Apellido, Nombre» (sin duplicar Dr./Dra. si ya venía en el nombre).
    Externo: texto tal cual (suele incluir título).
    """
    if medico is not None:
        apellido, nombre = _apellido_nombre_parts(medico)
        if not apellido or not nombre:
            user = getattr(medico, "user", None)
            if user is not None:
                apellido = apellido or (getattr(user, "last_name", None) or "").strip()
                nombre = nombre or (getattr(user, "first_name", None) or "").strip()
        nombre = _TITULO_MEDICO.sub("", nombre).strip()
        label = ", ".join(p for p in (apellido, nombre) if p)
        if not label:
            return fallback
        if not prefix_dr:
            return label
        if _TITULO_MEDICO.match(label):
            return label
        return f"Dr. {label}"

    ext = (externo_nombre or "").strip()
    if ext:
        return ext
    return fallback
