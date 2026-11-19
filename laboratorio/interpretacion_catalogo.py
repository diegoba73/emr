"""
Validación y normalización de campos_detalle / tabla_interpretacion del catálogo.

Usado por serializers, snapshots y PDF. No clasifica el resultado numérico.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.core.exceptions import ValidationError

MAX_CAMPOS_DETALLE = 20
MAX_ETIQUETA_LEN = 80
MAX_VALOR_LEN = 255
MAX_COLUMNAS = 8
MAX_FILAS = 30
MAX_CELDA_LEN = 80
MAX_TITULO_LEN = 120


def _as_str(value: Any, *, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)):
        raise ValidationError({field: "Debe ser texto."})
    return str(value).strip()


def normalize_campos_detalle(value: Any) -> list[dict[str, str]]:
    """Normaliza lista de {etiqueta, valor}. Lista vacía si no hay datos útiles."""
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValidationError({"campos_detalle": "Debe ser una lista."})
    if len(value) > MAX_CAMPOS_DETALLE:
        raise ValidationError(
            {"campos_detalle": f"Máximo {MAX_CAMPOS_DETALLE} campos."}
        )

    out: list[dict[str, str]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValidationError(
                {"campos_detalle": f"Ítem {i + 1}: debe ser un objeto."}
            )
        etiqueta = _as_str(item.get("etiqueta"), field="campos_detalle")
        valor = _as_str(item.get("valor"), field="campos_detalle")
        if not etiqueta and not valor:
            continue
        if not etiqueta:
            raise ValidationError(
                {"campos_detalle": f"Ítem {i + 1}: la etiqueta es obligatoria."}
            )
        if len(etiqueta) > MAX_ETIQUETA_LEN:
            raise ValidationError(
                {
                    "campos_detalle": (
                        f"Ítem {i + 1}: etiqueta máx. {MAX_ETIQUETA_LEN} caracteres."
                    )
                }
            )
        if len(valor) > MAX_VALOR_LEN:
            raise ValidationError(
                {
                    "campos_detalle": (
                        f"Ítem {i + 1}: valor máx. {MAX_VALOR_LEN} caracteres."
                    )
                }
            )
        out.append({"etiqueta": etiqueta, "valor": valor})
    return out


def normalize_tabla_interpretacion(value: Any) -> dict[str, Any] | None:
    """
    Normaliza {titulo?, columnas[], filas[][]} o None si vacío.

    Cada fila debe tener len(columnas) celdas.
    """
    if value in (None, "", {}):
        return None
    if not isinstance(value, dict):
        raise ValidationError({"tabla_interpretacion": "Debe ser un objeto."})

    titulo = _as_str(value.get("titulo"), field="tabla_interpretacion")
    if len(titulo) > MAX_TITULO_LEN:
        raise ValidationError(
            {
                "tabla_interpretacion": (
                    f"Título máx. {MAX_TITULO_LEN} caracteres."
                )
            }
        )

    columnas_raw = value.get("columnas")
    filas_raw = value.get("filas")
    if columnas_raw in (None, []) and filas_raw in (None, []):
        return None
    if not isinstance(columnas_raw, list):
        raise ValidationError(
            {"tabla_interpretacion": "columnas debe ser una lista."}
        )
    if filas_raw is None:
        filas_raw = []
    if not isinstance(filas_raw, list):
        raise ValidationError(
            {"tabla_interpretacion": "filas debe ser una lista."}
        )

    if not columnas_raw:
        raise ValidationError(
            {"tabla_interpretacion": "Definí al menos una columna."}
        )
    if len(columnas_raw) > MAX_COLUMNAS:
        raise ValidationError(
            {
                "tabla_interpretacion": (
                    f"Máximo {MAX_COLUMNAS} columnas."
                )
            }
        )
    if len(filas_raw) > MAX_FILAS:
        raise ValidationError(
            {"tabla_interpretacion": f"Máximo {MAX_FILAS} filas."}
        )

    columnas: list[str] = []
    for i, col in enumerate(columnas_raw):
        texto = _as_str(col, field="tabla_interpretacion")
        if not texto:
            raise ValidationError(
                {
                    "tabla_interpretacion": (
                        f"Columna {i + 1}: el encabezado no puede estar vacío."
                    )
                }
            )
        if len(texto) > MAX_CELDA_LEN:
            raise ValidationError(
                {
                    "tabla_interpretacion": (
                        f"Columna {i + 1}: máx. {MAX_CELDA_LEN} caracteres."
                    )
                }
            )
        columnas.append(texto)

    n = len(columnas)
    filas: list[list[str]] = []
    for r_i, fila in enumerate(filas_raw):
        if not isinstance(fila, list):
            raise ValidationError(
                {
                    "tabla_interpretacion": (
                        f"Fila {r_i + 1}: debe ser una lista de celdas."
                    )
                }
            )
        if len(fila) != n:
            raise ValidationError(
                {
                    "tabla_interpretacion": (
                        f"Fila {r_i + 1}: debe tener {n} celdas "
                        f"(una por columna)."
                    )
                }
            )
        celdas: list[str] = []
        for c_i, celda in enumerate(fila):
            texto = _as_str(celda, field="tabla_interpretacion")
            if len(texto) > MAX_CELDA_LEN:
                raise ValidationError(
                    {
                        "tabla_interpretacion": (
                            f"Fila {r_i + 1}, col {c_i + 1}: "
                            f"máx. {MAX_CELDA_LEN} caracteres."
                        )
                    }
                )
            celdas.append(texto)
        filas.append(celdas)

    out: dict[str, Any] = {"columnas": columnas, "filas": filas}
    if titulo:
        out["titulo"] = titulo
    return out


def snapshot_campos_detalle(tipo_examen) -> list[dict[str, str]]:
    raw = getattr(tipo_examen, "campos_detalle", None) or []
    try:
        return normalize_campos_detalle(raw)
    except ValidationError:
        # Catálogo corrupto: no bloquear carga; snapshot vacío seguro.
        return []


def snapshot_tabla_interpretacion(tipo_examen) -> dict[str, Any] | None:
    raw = getattr(tipo_examen, "tabla_interpretacion", None)
    try:
        return normalize_tabla_interpretacion(deepcopy(raw) if raw else None)
    except ValidationError:
        return None
