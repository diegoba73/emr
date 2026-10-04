"""
Examen de orina (tira + sedimento) asociado a urocultivo microbiológico.

Misma muestra física del cultivo; no crea pedido de lab. clínico (PAN_ORI).
Códigos alineados al catálogo ``ORI_*`` de orina completa.
"""
from __future__ import annotations

from typing import Any

# Tira reactiva
CAMPOS_TIRA: tuple[tuple[str, str], ...] = (
    ("ORI_COLOR", "Color"),
    ("ORI_ASP", "Aspecto"),
    ("ORI_DENS", "Densidad"),
    ("ORI_PH", "pH"),
    ("ORI_GLU", "Glucosa"),
    ("ORI_BIL", "Bilirrubina"),
    ("ORI_NIT", "Nitritos"),
    ("ORI_CET", "C. cetónicos"),
)

# Sedimento microscópico + conclusión
CAMPOS_SEDIMENTO: tuple[tuple[str, str], ...] = (
    ("ORI_CEL", "Células"),
    ("ORI_LEU", "Leucocitos"),
    ("ORI_HEM", "Hematíes"),
    ("ORI_PIO", "Piocitos"),
    ("ORI_MUC", "Mucus"),
    ("ORI_CRIS", "Cristales"),
    ("ORI_CONC", "Conclusión"),
)

CAMPOS_EXAMEN_ORINA: tuple[tuple[str, str], ...] = CAMPOS_TIRA + CAMPOS_SEDIMENTO
CODIGOS_EXAMEN_ORINA: frozenset[str] = frozenset(c for c, _ in CAMPOS_EXAMEN_ORINA)

LABELS_EXAMEN_ORINA: dict[str, str] = {c: label for c, label in CAMPOS_EXAMEN_ORINA}

# Tira + sedimento cualitativos (no color/aspecto/densidad/pH/conclusión).
VALOR_NO_CONTIENE = "NO CONTIENE"
CODIGOS_DEFAULT_NO_CONTIENE: frozenset[str] = frozenset(
    {
        "ORI_GLU",
        "ORI_BIL",
        "ORI_NIT",
        "ORI_CET",
        "ORI_LEU",
        "ORI_HEM",
        "ORI_CEL",
        "ORI_PIO",
        "ORI_MUC",
        "ORI_CRIS",
    }
)


def valor_inicial_resultado(tipo_examen) -> str:
    """Valor por defecto al crear ResultadoExamen (tira/sedimento → NO CONTIENE)."""
    codigo = (getattr(tipo_examen, "codigo", None) or "").strip().upper()
    if codigo in CODIGOS_DEFAULT_NO_CONTIENE:
        return VALOR_NO_CONTIENE
    return ""


def examen_orina_vacio() -> dict[str, str]:
    out: dict[str, str] = {}
    for codigo, _ in CAMPOS_EXAMEN_ORINA:
        out[codigo] = VALOR_NO_CONTIENE if codigo in CODIGOS_DEFAULT_NO_CONTIENE else ""
    return out


def normalizar_examen_orina(raw: Any) -> dict[str, str]:
    """Filtra claves desconocidas y fuerza strings (sin PHI extra)."""
    base = examen_orina_vacio()
    if not isinstance(raw, dict):
        return base
    for codigo in CODIGOS_EXAMEN_ORINA:
        val = raw.get(codigo)
        if val is None:
            continue
        base[codigo] = str(val).strip()
    return base


def examen_orina_tiene_datos(data: dict[str, str] | None) -> bool:
    """True si hay valores guardados (antes de rellenar defaults de UI)."""
    if not data:
        return False
    return any(str(v or "").strip() for v in data.values())


def estudio_admite_examen_orina(estudio) -> bool:
    """Solo urocultivo (por catálogo de cultivo o código legado tipo_estudio)."""
    cultivo = getattr(estudio, "tipo_cultivo", None)
    if cultivo is not None:
        codigo = (getattr(cultivo, "codigo", None) or "").strip().upper()
        if codigo:
            return codigo == "UROCULTIVO"
    tipo = (getattr(estudio, "tipo_estudio", None) or "").strip().upper()
    return tipo == "UROCULTIVO"
