"""
Examen microscópico directo asociado al cultivo (misma muestra).

Apartado general del informe: «Examen microscópico directo».
Dentro se distinguen las técnicas realmente cargadas:
- Examen en fresco
- Tinción de Gram
- Examen micológico (KOH)
- Examen parasitológico (materia fecal)

No todos los cultivos admiten las mismas técnicas.
Solo se informa si hay datos guardados.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

TecnicaId = Literal["fresco", "gram", "koh", "parasito"]

# --- Campos por técnica -------------------------------------------------------

CAMPOS_FRESCO_GENITAL: tuple[tuple[str, str], ...] = (
    ("EXF_CEL", "Células"),
    ("EXF_HEM", "Hematíes"),
    ("EXF_LEU", "Leucocitos"),
    ("EXF_TRICH", "Trichomonas Spp."),
)

CAMPOS_FRESCO_LIQUIDO: tuple[tuple[str, str], ...] = (
    ("EXF_ASP", "Aspecto"),
    ("EXF_CEL", "Células"),
    ("EXF_HEM", "Hematíes"),
    ("EXF_LEU", "Leucocitos"),
)

CAMPOS_GRAM: tuple[tuple[str, str], ...] = (
    ("EXF_GRAM", "Tinción de Gram"),
)

CAMPOS_KOH: tuple[tuple[str, str], ...] = (
    ("EXF_MICOL", "Examen micológico (KOH)"),
)

CAMPOS_PARASITO: tuple[tuple[str, str], ...] = (
    ("EXF_PAR_MACRO", "Examen macroscópico"),
    ("EXF_PAR_MICRO", "Examen microscópico"),
    ("EXF_PAR_PROTO", "Protozoarios"),
    ("EXF_PAR_HELM", "Helmintos (huevos / larvas)"),
)

TITULO_TECNICA_UI: dict[TecnicaId, str] = {
    "fresco": "Examen en fresco",
    "gram": "Tinción de Gram",
    "koh": "Examen micológico (KOH)",
    "parasito": "Examen parasitológico",
}

TITULO_TECNICA_INFORME: dict[TecnicaId, str] = {
    "fresco": "Examen en fresco",
    "gram": "Tinción de Gram",
    "koh": "Examen micológico (KOH)",
    "parasito": "Examen parasitológico",
}

TITULO_APARTADO_INFORME = "EXAMEN MICROSCOPICO DIRECTO"
TITULO_APARTADO_UI = "Examen microscópico directo"


class SeccionTecnica(TypedDict):
    tecnica: TecnicaId
    titulo_ui: str
    titulo_informe: str
    campos: tuple[tuple[str, str], ...]


# Cultivo → técnicas habilitadas (con su set de campos de fresco si aplica).
def _secciones(
    *items: tuple[TecnicaId, tuple[tuple[str, str], ...]]
) -> tuple[SeccionTecnica, ...]:
    out: list[SeccionTecnica] = []
    for tecnica, campos in items:
        out.append(
            {
                "tecnica": tecnica,
                "titulo_ui": TITULO_TECNICA_UI[tecnica],
                "titulo_informe": TITULO_TECNICA_INFORME[tecnica],
                "campos": campos,
            }
        )
    return tuple(out)


CULTIVO_A_SECCIONES: dict[str, tuple[SeccionTecnica, ...]] = {
    # Genitales: fresco + KOH (no se llama “fresco” al KOH).
    "VAGINAL": _secciones(
        ("fresco", CAMPOS_FRESCO_GENITAL),
        ("koh", CAMPOS_KOH),
    ),
    "URETRAL": _secciones(
        ("fresco", CAMPOS_FRESCO_GENITAL),
        ("koh", CAMPOS_KOH),
    ),
    # Materia fecal.
    "COPROCULTIVO": _secciones(("parasito", CAMPOS_PARASITO)),
    # Piel / uñas / pelos → solo KOH.
    "HONGOS_ESCAMAS": _secciones(("koh", CAMPOS_KOH)),
    "HONGOS_PELOS": _secciones(("koh", CAMPOS_KOH)),
    "HONGOS_UNAS": _secciones(("koh", CAMPOS_KOH)),
    # Líquidos biológicos: fresco + Gram.
    "LCR": _secciones(("fresco", CAMPOS_FRESCO_LIQUIDO), ("gram", CAMPOS_GRAM)),
    "LIQUIDO_PLEURAL": _secciones(
        ("fresco", CAMPOS_FRESCO_LIQUIDO), ("gram", CAMPOS_GRAM)
    ),
    "LIQUIDO_ASCITICO": _secciones(
        ("fresco", CAMPOS_FRESCO_LIQUIDO), ("gram", CAMPOS_GRAM)
    ),
    "LIQUIDO_PERITONEAL": _secciones(
        ("fresco", CAMPOS_FRESCO_LIQUIDO), ("gram", CAMPOS_GRAM)
    ),
    "LIQUIDO_SINOVIAL": _secciones(
        ("fresco", CAMPOS_FRESCO_LIQUIDO), ("gram", CAMPOS_GRAM)
    ),
    # Gram (sin fresco): esputo, heridas, faríngeo, hemocultivo.
    "ESPUTO": _secciones(("gram", CAMPOS_GRAM)),
    "HERIDA_ABSCESO": _secciones(("gram", CAMPOS_GRAM)),
    "PIEL_PARTES_BLANDAS": _secciones(("gram", CAMPOS_GRAM)),
    "NASOFARINGEO": _secciones(("gram", CAMPOS_GRAM)),
    "HEMOCULTIVO": _secciones(("gram", CAMPOS_GRAM)),
}

CODIGOS_CULTIVO_ADMITEN_EXAMEN_FRESCO: frozenset[str] = frozenset(CULTIVO_A_SECCIONES)

# Unión de todos los campos (persistencia JSON compartida).
_seen: dict[str, str] = {}
for _secciones_cultivo in CULTIVO_A_SECCIONES.values():
    for _sec in _secciones_cultivo:
        for _codigo, _label in _sec["campos"]:
            if _codigo not in _seen:
                _seen[_codigo] = _label
CAMPOS_EXAMEN_FRESCO: tuple[tuple[str, str], ...] = tuple(_seen.items())
CODIGOS_EXAMEN_FRESCO: frozenset[str] = frozenset(_seen)
LABELS_EXAMEN_FRESCO: dict[str, str] = dict(_seen)


def codigo_cultivo_estudio(estudio) -> str:
    cultivo = getattr(estudio, "tipo_cultivo", None)
    if cultivo is not None:
        codigo = (getattr(cultivo, "codigo", None) or "").strip().upper()
        if codigo:
            return codigo
    return (getattr(estudio, "tipo_estudio", None) or "").strip().upper()


def secciones_examen_directo(estudio_or_codigo) -> tuple[SeccionTecnica, ...]:
    if isinstance(estudio_or_codigo, str):
        codigo = estudio_or_codigo.strip().upper()
    else:
        codigo = codigo_cultivo_estudio(estudio_or_codigo)
    return CULTIVO_A_SECCIONES.get(codigo, ())


def campos_examen_fresco_para(estudio_or_codigo) -> tuple[tuple[str, str], ...]:
    """Todos los campos editables del cultivo (aplanados)."""
    campos: list[tuple[str, str]] = []
    seen: set[str] = set()
    for sec in secciones_examen_directo(estudio_or_codigo):
        for codigo, label in sec["campos"]:
            if codigo not in seen:
                seen.add(codigo)
                campos.append((codigo, label))
    return tuple(campos)


def titulo_informe_examen_fresco(estudio_or_codigo=None) -> str:
    """Apartado general del PDF (siempre el mismo)."""
    return TITULO_APARTADO_INFORME


def titulo_ui_examen_fresco(estudio_or_codigo=None) -> str:
    """Etiqueta de solapa UI (siempre el mismo apartado general)."""
    return TITULO_APARTADO_UI


def examen_fresco_vacio() -> dict[str, str]:
    return {codigo: "" for codigo, _ in CAMPOS_EXAMEN_FRESCO}


def normalizar_examen_fresco(raw: Any) -> dict[str, str]:
    """Filtra claves desconocidas y fuerza strings."""
    base = examen_fresco_vacio()
    if not isinstance(raw, dict):
        return base
    for codigo in CODIGOS_EXAMEN_FRESCO:
        val = raw.get(codigo)
        if val is None:
            continue
        base[codigo] = str(val).strip()
    return base


def seccion_tiene_datos(sec: SeccionTecnica, data: dict[str, str]) -> bool:
    return any(str(data.get(codigo) or "").strip() for codigo, _ in sec["campos"])


def examen_fresco_tiene_datos(data: dict[str, str] | None) -> bool:
    """True si hay al menos un valor guardado (sección informable)."""
    if not data:
        return False
    return any(str(v or "").strip() for v in data.values())


def estudio_admite_examen_fresco(estudio) -> bool:
    return bool(secciones_examen_directo(estudio))


# Compat: algunos tests/código hablaban de “perfil”.
def perfil_examen_fresco(estudio_or_codigo) -> str | None:
    secs = secciones_examen_directo(estudio_or_codigo)
    if not secs:
        return None
    # Etiqueta corta del primer “modo” dominante (solo para tests/legacy).
    tecnicas = {s["tecnica"] for s in secs}
    if tecnicas == {"parasito"}:
        return "parasito"
    if tecnicas == {"koh"}:
        return "micologico"
    if tecnicas == {"gram"}:
        return "gram"
    if "fresco" in tecnicas and "koh" in tecnicas:
        return "genital"
    if "fresco" in tecnicas:
        return "liquido"
    return "directo"
