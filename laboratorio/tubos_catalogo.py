"""
Asignación de tipo de tubo (TipoContenedor) por código de TipoExamen
y/o tipo de muestra requerida.
"""

from __future__ import annotations

# Códigos de contenedor (laboratorio.TipoContenedor.codigo)
EDTA = "EDTA"
CITRATO = "CITRATO"
CITRATO_VSG = "CITRATO_VSG"
HEPARINA = "HEPARINA"
SUERO = "SUERO"
FRASCO_ORINA = "FRASCO_ORINA"
BIDON_ORINA_24H = "BIDON_ORINA_24H"

CONTENEDORES_SEED = (
    (EDTA, "Tubo EDTA", "Morado", "EDTA K2"),
    (CITRATO, "Tubo Citrato coagulación", "Celeste", "Citrato de sodio"),
    (
        CITRATO_VSG,
        "Tubo Citrato VSG",
        "Negro",
        "Citrato de sodio trisódico 3,8%",
    ),
    (HEPARINA, "Tubo Heparina", "Verde", "Heparina de litio"),
    (SUERO, "Tubo Suero", "Rojo", "Sin anticoagulante / gel"),
)

CONTENEDORES_EXTRA = (
    (FRASCO_ORINA, "Frasco de orina", "Ámbar", "Sin aditivo"),
    (
        BIDON_ORINA_24H,
        "Bidón orina 24 hs",
        "Ámbar",
        "Recolección 24 hs (sin aditivo / según protocolo)",
    ),
)

CONTENEDORES_TODOS = (*CONTENEDORES_SEED, *CONTENEDORES_EXTRA)

MUESTRA_ORINA = "ORINA"
MUESTRA_ORINA_24H = "ORINA_24_H"

# Hemograma + HbA1c en sangre total EDTA (VSG NO: tubo negro propio)
_EDTA = frozenset(
    {
        "HEMATIES",
        "HTO",
        "HGB",
        "HB",
        "VCM",
        "CHCM",
        "RDW",
        "LEUCO",
        "NEUT_CAY",
        "NEUT_SEG",
        "EOS",
        "BAS",
        "LINF",
        "MONO",
        "PLAQ",
        "PL",
        "HBA1C",
    }
)

# Coagulación (tapa celeste) — distinto del VSG
_CITRATO = frozenset({"TP", "PP", "INR", "KPTT", "DDIM", "DD"})

# Eritrosedimentación: tubo tapa negra, citrato 3,8%
_CITRATO_VSG = frozenset({"VSG"})

# Gases / lactato / calcio iónico (sangre total heparina)
# EAB arterial y venoso = jeringas distintas (no compartir etiqueta)
_HEPARINA_GASES = frozenset({"EAB_ART", "EAB_VEN", "LACT", "LACPLA", "CA_ION", "CAIISE", "CAIE"})
_EAB_JERINGA_INDIVIDUAL = frozenset({"EAB_ART", "EAB_VEN"})

# Rutina de química: 1 tubo heparina (plasma) alcanza ~200 µL
_QUIMICA_RUTINA = frozenset(
    {
        "GLU",
        "UREA",
        "CREATI",
        "COL_TOT",
        "HDL",
        "LDL",
        "COL_NO_LDL",
        "TG",
        "GOT",
        "GPT",
        "FAL",
        "BIL_T",
        "BIL_D",
        "NA",
        "K",
        "CL",
    }
)

_HEPARINA = _HEPARINA_GASES | _QUIMICA_RUTINA

# Orina al azar / completa → frasco
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
        "PROT_U_AZ",
        # Dual (también en paneles 24 hs): default frasco; la orden puede remapear a bidón
        "NA_U",
        "K_U",
        "CL_U",
        "CREA_U",
        "MICROALB",
    }
)

# Orina de 24 hs → bidón (recolección de todo el día). 1 bidón alcanza para todos.
_ORINA_24H = frozenset(
    {
        "PROT_U_24",
        "CLEAR_CREA",
        "DIUR",
        "ALB24",
        "PROTT24",
    }
)

# Códigos duales: frasco (al azar) o bidón (si la orden pide panel/contexto 24 hs)
_ORINA_DUAL = frozenset({"NA_U", "K_U", "CL_U", "CREA_U", "MICROALB"})

PANELES_ORINA_24H = frozenset({"PAN_IONO_U24", "PAN_CLEAR", "PAN_MALB24"})

MUESTRA_CANONICA_POR_ANALITO: dict[str, str] = {
    **{c: "SANGRE_EDTA" for c in _EDTA},
    **{c: "PLASMA_CITRATO" for c in _CITRATO},
    **{c: "SANGRE_CITRATO_VSG" for c in _CITRATO_VSG},
    **{c: "SANGRE_HEPARINA" for c in (_HEPARINA_GASES - _EAB_JERINGA_INDIVIDUAL)},
    "EAB_ART": "SANGRE_HEPARINA_ART",
    "EAB_VEN": "SANGRE_HEPARINA_VEN",
    **{c: "PLASMA_HEPARINA" for c in _QUIMICA_RUTINA},
    **{c: MUESTRA_ORINA for c in _FRASCO_ORINA},
    **{c: MUESTRA_ORINA_24H for c in _ORINA_24H},
}


def es_muestra_orina_24h(muestra_codigo: str | None, muestra_nombre: str | None = None) -> bool:
    """True si el material indica recolección de orina de 24 horas."""
    raw = f"{muestra_codigo or ''} {muestra_nombre or ''}".upper()
    raw = raw.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    if "ORINA" not in raw:
        return False
    return "24" in raw


def _tubo_por_muestra(muestra_codigo: str | None, muestra_nombre: str | None = None) -> str | None:
    """Infere tubo desde el tipo de muestra (material IACA)."""
    raw = f"{muestra_codigo or ''} {muestra_nombre or ''}".upper()
    raw = raw.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")

    if not raw.strip():
        return None

    # Orina 24 hs → bidón (antes que frasco genérico)
    if es_muestra_orina_24h(muestra_codigo, muestra_nombre):
        return BIDON_ORINA_24H

    if "ORINA" in raw or raw.strip() in {"ORINA"}:
        return FRASCO_ORINA

    if "VSG" in raw or "WESTERGREN" in raw or "CITRATO_VSG" in raw:
        return CITRATO_VSG

    if "EDTA" in raw or "SANGRE ENTERA" in raw or "SANGRE SECA" in raw:
        return EDTA

    if "CITRATO" in raw:
        return CITRATO

    if "HEPARINA" in raw or "HEPAINA" in raw:
        return HEPARINA

    if "SUERO" in raw or raw.strip() in {"SANGRE", "SANGRE_2"}:
        return SUERO

    if "PLASMA" in raw:
        return SUERO

    return None


def tubo_codigo_para_examen(
    codigo: str,
    muestra: str | None = None,
    *,
    muestra_nombre: str | None = None,
) -> str:
    """
    Devuelve el código de TipoContenedor para un examen.

    Prioridad:
    1) Reglas por código de analito.
    2) Inferencia por tipo de muestra / material.
    3) Default: tubo suero.
    """
    c = (codigo or "").upper().strip()
    if c in _EDTA:
        return EDTA
    if c in _CITRATO_VSG:
        return CITRATO_VSG
    if c in _CITRATO:
        return CITRATO
    if c in _QUIMICA_RUTINA or c in _HEPARINA_GASES:
        return HEPARINA
    if c in _ORINA_24H:
        return BIDON_ORINA_24H
    if c in _FRASCO_ORINA or c.startswith("ORI_"):
        return FRASCO_ORINA

    por_muestra = _tubo_por_muestra(muestra, muestra_nombre)
    if por_muestra:
        return por_muestra

    m = (muestra or "").upper().strip()
    if es_muestra_orina_24h(m):
        return BIDON_ORINA_24H
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
