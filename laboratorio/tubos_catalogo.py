"""
Asignación de tipo de tubo (TipoContenedor) por código de TipoExamen.

Reglas clínicas estándar para el catálogo de solicitud en papel.
"""

from __future__ import annotations

# Códigos de contenedor (laboratorio.TipoContenedor.codigo)
EDTA = "EDTA"
CITRATO = "CITRATO"
HEPARINA = "HEPARINA"
SUERO = "SUERO"
FRASCO_ORINA = "FRASCO_ORINA"

CONTENEDORES_SEED = (
    (EDTA, "Tubo EDTA", "Morado", "EDTA K2"),
    (CITRATO, "Tubo Citrato", "Celeste", "Citrato de sodio"),
    (HEPARINA, "Tubo Heparina", "Verde", "Heparina de litio"),
    (SUERO, "Tubo Suero", "Rojo", "Sin anticoagulante / gel"),
)

CONTENEDORES_EXTRA = (
    (FRASCO_ORINA, "Frasco de orina", "Ámbar", "Sin aditivo"),
)

CONTENEDORES_TODOS = (*CONTENEDORES_SEED, *CONTENEDORES_EXTRA)

# Hemograma + analitos en sangre total EDTA
_EDTA = frozenset(
    {
        "HEMATIES",
        "HTO",
        "HGB",
        "RDW",
        "LEU",
        "NEUT_CAY",
        "NEUT_SEG",
        "EOS",
        "BAS",
        "LINF",
        "MONO",
        "PLAQ",
        "HBA1C",
        "VSG",
    }
)

# Coagulación
_CITRATO = frozenset({"TP", "PP", "INR", "KPTT", "DDIM"})

# Gases / lactato / calcio iónico (sangre total heparina)
_HEPARINA = frozenset({"EAB_ART", "EAB_VEN", "LACT", "CA_ION"})

# Orina (frasco)
_FRASCO_ORINA = frozenset(
    {
        "ORI_COLOR",
        "ORI_ASP",
        "ORI_DENS",
        "ORI_PH",
        "ORI_BIL",
        "ORI_NIT",
        "ORI_CET",
        "ORI_CEL",
        "ORI_LEU",
        "ORI_HEM",
        "ORI_PIO",
        "ORI_MUC",
        "ORI_CRIS",
        "ORI_CONC",
        "NA_U",
        "K_U",
        "CL_U",
        "CREA_U",
        "DIUR",
        "CLEAR_CREA",
        "MICROALB",
        "PROT_U_24",
        "PROT_U_AZ",
    }
)


def tubo_codigo_para_examen(codigo: str, muestra: str | None = None) -> str:
    """
    Devuelve el código de TipoContenedor para un examen.
    Si no está en listas específicas: SUERO (sangre) o FRASCO_ORINA (orina).
    """
    c = (codigo or "").upper().strip()
    if c in _EDTA:
        return EDTA
    if c in _CITRATO:
        return CITRATO
    if c in _HEPARINA:
        return HEPARINA
    if c in _FRASCO_ORINA or c.startswith("ORI_"):
        return FRASCO_ORINA
    m = (muestra or "").upper().strip()
    if m == "ORINA" or c.endswith("_U") or "U_" in c:
        return FRASCO_ORINA
    return SUERO


def mapa_tubos_catalogo_papel() -> dict[str, str]:
    """codigo examen → codigo contenedor, según EXAMENES del papel."""
    from laboratorio.catalogo_solicitud_papel import EXAMENES

    return {
        item["codigo"]: tubo_codigo_para_examen(item["codigo"], item.get("muestra"))
        for item in EXAMENES
    }
