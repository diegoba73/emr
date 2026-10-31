"""
Asignación de tipo de tubo (TipoContenedor) por código de TipoExamen
y/o tipo de muestra requerida.
"""

from __future__ import annotations

# Códigos de contenedor (laboratorio.TipoContenedor.codigo)
EDTA = "EDTA"
CITRATO = "CITRATO"
ERITRO = "ERITRO"
# Alias legacy (mismo código efectivo)
CITRATO_VSG = ERITRO
HEPARINA = "HEPARINA"
SUERO = "SUERO"
FRASCO_ORINA = "FRASCO_ORINA"
FRASCO_ESTERIL = "FRASCO_ESTERIL"
BIDON_ORINA_24H = "BIDON_ORINA_24H"

CONTENEDORES_SEED = (
    (EDTA, "Tubo EDTA", "Morado", "EDTA K2"),
    (CITRATO, "Tubo Citrato coagulación", "Celeste", "Citrato de sodio"),
    (
        ERITRO,
        "Tubo Eritro (VSG)",
        "Negro",
        "Citrato de sodio trisódico 3,8%",
    ),
    (HEPARINA, "Tubo Heparina", "Verde", "Heparina de litio"),
    (SUERO, "Tubo Suero", "Rojo", "Sin anticoagulante / gel"),
)

CONTENEDORES_EXTRA = (
    (FRASCO_ORINA, "Frasco de orina", "Ámbar", "Sin aditivo"),
    (
        FRASCO_ESTERIL,
        "Frasco / tubo estéril",
        "Transparente",
        "Sin aditivo (líquidos y secreciones)",
    ),
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
MUESTRA_ERITRO = "SANGRE_ERITRO"
# Alias legacy del material VSG
MUESTRA_CITRATO_VSG = MUESTRA_ERITRO

# Hemograma + HbA1c en sangre total EDTA (VSG NO: tubo eritro propio)
_EDTA = frozenset(
    {
        "HEMATIES",
        "HTO",
        "HGB",
        "HB",
        "VCM",
        "HCM",
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
        "GRUPO",
    }
)

# Coagulación (tapa celeste) — distinto del VSG/eritro
_CITRATO = frozenset({"TP", "PP", "INR", "KPTT", "DDIM", "DD"})

# Eritrosedimentación: tubo eritro (tapa negra, citrato 3,8%)
_ERITRO = frozenset({"VSG"})
_CITRATO_VSG = _ERITRO  # alias legacy

# Parámetros de contexto clínico: no generan tubo/jeringa propia
EXAMENES_SIN_CONTENEDOR = frozenset({"FIO2"})

# Derivados de informe: figuran en el panel pero no tienen material físico propio.
# (misma lista que laboratorio.calculos_derivados.CODIGOS_CALCULADOS; se duplica
# acá para no acoplar tubos ↔ fórmulas en import).
EXAMENES_CALCULADOS_SIN_TUBO = frozenset(
    {
        "LDL",
        "VLDL",
        "COL_NO_LDL",
        "COL_RESID",
        "RATIO_CT_HDL",
        "BIL_I",
        "CF",
        "SAT_FE",
        "TRANS",
        "CLEAR_CREA",
        "PROT_U_24",
        "NA_U24",
        "K_U24",
        "CL_U24",
        "MICROALB_24",
        "CA_U24",
        "MG_U24",
        "P_U24",
        "AU_U24",
        "UREA_U24",
        "CREA_U24",
        "RAC",
        "TFG",
    }
)

# Gases / lactato / calcio iónico (sangre total heparina)
# EAB arterial y venoso = jeringas distintas (no compartir etiqueta)
_EAB_ART = frozenset({"PH_ART", "PO2_ART", "PCO2_ART", "SAT_O2_ART", "HCO3_ART", "BE_ART"})
_EAB_VEN = frozenset({"PH_VEN", "PO2_VEN", "PCO2_VEN", "SAT_O2_VEN", "HCO3_VEN", "BE_VEN"})
_EAB_JERINGA_INDIVIDUAL = _EAB_ART | _EAB_VEN
# Lactato / Ca iónico: misma jeringa EAB (art preferida; si no, ven).
# Sin EAB en la orden → heparina propia (etiqueta SANGRE_HEPARINA).
_CODIGOS_HEPARINA_COMPARTEN_EAB = frozenset(
    {"LACT", "LACPLA", "CA_ION", "CAIISE", "CAIE"}
)
# Alias legacy (imports / compat).
_CODIGOS_LACTATO_COMPARTEN_EAB = frozenset({"LACT", "LACPLA"})
_HEPARINA_SUELTOS = _CODIGOS_HEPARINA_COMPARTEN_EAB
_HEPARINA_GASES = _EAB_JERINGA_INDIVIDUAL | _HEPARINA_SUELTOS
_MUESTRAS_HEPARINA_SANGRE = frozenset(
    {"SANGRE_HEPARINA", "SANGRE_HEPARINA_ART", "SANGRE_HEPARINA_VEN"}
)

# Química de rutina: mismo tubo suero que el resto de bioquímica
_QUIMICA_RUTINA = frozenset(
    {
        "GLU",
        "GLU_0",
        "GLU120",
        "UREA",
        "CREATI",
        "COL_TOT",
        "HDL",
        "LDL",
        "VLDL",
        "COL_NO_LDL",
        "COL_RESID",
        "RATIO_CT_HDL",
        "TG",
        "GOT",
        "GPT",
        "FAL",
        "BIL_T",
        "BIL_D",
        "BIL_I",
        "NA",
        "K",
        "CL",
    }
)

# Solo gases / lactato / Ca iónico siguen en heparina
_HEPARINA = _HEPARINA_GASES

# Orina al azar / completa → frasco
_FRASCO_ORINA = frozenset(
    {
        "ORI_COLOR",
        "ORI_ASP",
        "ORI_DENS",
        "ORI_PH",
        "ORI_GLU",
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
        "PROT_U_AZ",        # Dual (también en paneles 24 hs): default frasco; la orden puede remapear a bidón
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
        "PROT_U_EQ",
        "CLEAR_CREA",
        "DIUR",
        "ALB24",
        "PROTT24",
        "MICROALB_24",
        "NA_U24",
        "K_U24",
        "CL_U24",
        "CA_U",
        "CA_U24",
        "MG_U",
        "MG_U24",
        "P_U",
        "P_U24",
        "AU_U",
        "AU_U24",
        "UREA_U",
        "UREA_U24",
        "CREA_U24",
    }
)

# Códigos duales: frasco (al azar) o bidón (si la orden pide panel/contexto 24 hs)
_ORINA_DUAL = frozenset({"NA_U", "K_U", "CL_U", "CREA_U", "MICROALB"})

PANELES_ORINA_24H = frozenset(
    {
        "PAN_IONO_U24",
        "PAN_CLEAR",
        "PAN_MALB24",
        "PAN_PROT24",
        "PAN_CA_U24",
        "PAN_MG_U24",
        "PAN_P_U24",
        "PAN_AU_U24",
        "PAN_UREA_U24",
        "PAN_CREA_U24",
    }
)

MUESTRA_CANONICA_POR_ANALITO: dict[str, str] = {
    **{c: "SANGRE_EDTA" for c in _EDTA},
    **{c: "PLASMA_CITRATO" for c in _CITRATO},
    **{c: MUESTRA_ERITRO for c in _ERITRO},
    **{c: "SANGRE_HEPARINA" for c in (_HEPARINA_GASES - _EAB_JERINGA_INDIVIDUAL)},
    **{c: "SANGRE_HEPARINA_ART" for c in _EAB_ART},
    **{c: "SANGRE_HEPARINA_VEN" for c in _EAB_VEN},
    **{c: SUERO for c in _QUIMICA_RUTINA},
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

    if "FECAL" in raw or "HECES" in raw or "MATERIA_FECAL" in raw:
        return FRASCO_ORINA

    if (
        "VSG" in raw
        or "WESTERGREN" in raw
        or "CITRATO_VSG" in raw
        or "ERITRO" in raw
        or "SANGRE_ERITRO" in raw
    ):
        return ERITRO

    if "EDTA" in raw or "SANGRE ENTERA" in raw or "SANGRE SECA" in raw:
        return EDTA

    if "CITRATO" in raw:
        return CITRATO

    # Plasma heparina de química → suero (mismo tubo rojo)
    if "PLASMA" in raw and ("HEPARINA" in raw or "HEPAINA" in raw):
        return SUERO

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
) -> str | None:
    """
    Devuelve el código de TipoContenedor para un examen, o None si no aplica tubo.

    Prioridad:
    1) Parámetros de contexto (p. ej. FiO2) → None.
    2) Reglas por código de analito.
    3) Inferencia por tipo de muestra / material.
    4) Default: tubo suero.
    """
    c = (codigo or "").upper().strip()
    if c in EXAMENES_SIN_CONTENEDOR or c in EXAMENES_CALCULADOS_SIN_TUBO:
        return None

    # Materiales de pedido (LCR, líquidos, secreciones, tejidos) → frasco estéril.
    # Antes que reglas de sangre (GLU/LACT/…) para no pisar analitos homónimos.
    from laboratorio.materiales_pedido_catalogo import (
        CONTENEDOR_ESTERIL,
        todas_muestras_clinicas,
    )

    m_up = (muestra or "").upper().strip()
    # LCR / Esputo: frasco estéril siempre (también por sufijo de código).
    if m_up == "LCR" or c.endswith("_LCR"):
        return FRASCO_ESTERIL
    if m_up == "ESPUTO" or c.endswith("_ESP"):
        return FRASCO_ESTERIL
    if m_up and m_up in todas_muestras_clinicas():
        return CONTENEDOR_ESTERIL

    if c in _EDTA:
        return EDTA
    if c in _ERITRO:
        return ERITRO
    if c in _CITRATO:
        return CITRATO
    if c in _HEPARINA_GASES:
        return HEPARINA
    if c in _QUIMICA_RUTINA:
        return SUERO
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


def mapa_tubos_catalogo_papel() -> dict[str, str | None]:
    """codigo examen → codigo contenedor (None si no aplica), según EXAMENES del papel."""
    from laboratorio.catalogo_solicitud_papel import EXAMENES

    return {
        item["codigo"]: tubo_codigo_para_examen(item["codigo"], item.get("muestra"))
        for item in EXAMENES
    }
