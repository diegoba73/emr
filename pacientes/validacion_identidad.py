"""Validación conservadora de nombre/apellido/DNI al alta y edición por API.

No reescribe fichas legacy en BD: solo bloquea guardar valores basura
cuando el operador envía esos campos.
"""
from __future__ import annotations

import re
from typing import Any

# Al menos una letra unicode (no dígito ni signo).
_LETRA = re.compile(r"[^\W\d_]", re.UNICODE)
_SOLO_DIGITOS = re.compile(r"^\d+$")

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
        f"El {campo} no parece válido. Usá un nombre real "
        "(no puntos, guiones ni símbolos solos)."
    )


def mensaje_dni_dudoso() -> str:
    return (
        "El DNI/documento parece inválido o de prueba "
        "(muy corto, todos iguales o placeholder tipo 11111). "
        "Corregilo antes de guardar."
    )


def nombre_o_apellido_valido(value: Any) -> bool:
    """True si hay ≥2 letras (unicode). Rechaza ``.``, ``...``, ``-``, ``111``."""
    text = _as_text(value)
    if not text:
        return False
    letras = _LETRA.findall(text)
    return len(letras) >= 2


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
