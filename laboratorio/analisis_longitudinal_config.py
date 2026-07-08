"""
Umbrales de variación histórica (% absoluto) para clasificar cambios entre resultados.

Los valores son porcentajes de cambio respecto al resultado anterior del mismo analito.
Se puede sobreescribir por ``codigo`` de ``TipoExamen``.
"""
from __future__ import annotations

from typing import TypedDict


class UmbralesVariacion(TypedDict):
    estable: float
    moderada: float
    brusca: float


UMBRALES_DEFAULT: UmbralesVariacion = {
    "estable": 10.0,
    "moderada": 25.0,
    "brusca": 40.0,
}

# Parámetros con variación biológica habitualmente menor o mayor.
UMBRALES_POR_CODIGO: dict[str, UmbralesVariacion] = {
    # Ionograma: cambios pequeños pueden ser clínicamente relevantes
    "NA": {"estable": 3.0, "moderada": 5.0, "brusca": 8.0},
    "K": {"estable": 5.0, "moderada": 10.0, "brusca": 15.0},
    "CL": {"estable": 3.0, "moderada": 6.0, "brusca": 10.0},
    # Coagulación
    "INR": {"estable": 10.0, "moderada": 20.0, "brusca": 30.0},
    # Hemograma — leucocitos/plaquetas con mayor rango fisiológico
    "LEU": {"estable": 15.0, "moderada": 30.0, "brusca": 50.0},
    "PLAQ": {"estable": 15.0, "moderada": 30.0, "brusca": 45.0},
}


def umbrales_para_codigo(codigo: str) -> UmbralesVariacion:
    key = (codigo or "").strip().upper()
    return UMBRALES_POR_CODIGO.get(key, UMBRALES_DEFAULT)
