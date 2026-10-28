"""Validación conservadora de nombre/apellido/DNI al alta y edición por API.

No reescribe fichas legacy en BD: solo bloquea guardar valores basura
cuando el operador envía esos campos.
"""
from __future__ import annotations

import re
from typing import Any

_SOLO_LETRAS = re.compile(r"^[^\W\d_]+$", re.UNICODE)
_SOLO_DIGITOS = re.compile(r"^\d+$")
# Solo letras unicode y espacios entre palabras (sin puntos, guiones, dígitos).
_NOMBRE_PERMITIDO = re.compile(r"^[^\W\d_]+(?:\s+[^\W\d_]+)*$", re.UNICODE)

# Placeholders frecuentes de carga de prueba / “para salir del paso”.
# Solo placeholders cortos / obvios. No listar DNI de 7–8 dígitos “bonitos”
# (pueden ser reales). Los de un solo dígito repetido los atrapa ``len(set)==1``.
_DNI_PLACEHOLDER = frozenset(
    {
        "0",
        "00",
        "000",
        "0000",
        "00000",
        "000000",
        "11111",
        "12345",
        "123456",
        "99999",
    }
)

# DNI argentino típico ≥7; 6 deja margen a docs cortos sin aceptar 11111 (5).
_DNI_DIGITOS_MIN = 6


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def mensaje_nombre_invalido(campo: str = "nombre") -> str:
    return (
        f"El {campo} debe ser completo, solo letras y espacios "
        f"(ej. DIEGO o DIEGO ARMANDO). No uses puntos, abreviaturas "
        f"ni letras sueltas."
    )


def mensaje_dni_dudoso() -> str:
    return (
        "El DNI/documento parece inválido o de prueba "
        "(muy corto, todos iguales o placeholder tipo 11111). "
        "Corregilo antes de guardar."
    )


def nombre_o_apellido_valido(value: Any) -> bool:
    """Nombre/apellido completo: solo letras y espacios; cada palabra ≥2 letras.

    Acepta ``DIEGO``, ``DIEGO ARMANDO``, ``BAULDE``, ``DE LA CRUZ``.
    Rechaza ``.``, ``d.d.``, ``D``, guiones, dígitos y cualquier símbolo.
    """
    text = _as_text(value)
    if not text:
        return False
    # Colapsar espacios internos para validar forma canónica.
    compact = " ".join(text.split())
    if not _NOMBRE_PERMITIDO.match(compact):
        return False
    for palabra in compact.split(" "):
        if len(palabra) < 2:
            return False
        if not _SOLO_LETRAS.match(palabra):
            return False
    return True


def dni_dudoso(value: Any) -> bool:
    """True si el documento es claramente placeholder / sospechoso."""
    text = _as_text(value)
    if not text:
        return True
    # Conservar letras (pasaporte): no aplicar reglas de solo-dígitos.
    alnum = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    if not alnum:
        return True
    if alnum in _DNI_PLACEHOLDER:
        return True
    if _SOLO_DIGITOS.match(alnum):
        if len(alnum) < _DNI_DIGITOS_MIN:
            return True
        if len(set(alnum)) == 1:
            return True
    return False
