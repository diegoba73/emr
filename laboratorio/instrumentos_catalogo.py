"""Catálogo de códigos de analito del analizador → TipoExamen.codigo LIMS."""
from __future__ import annotations

# Sysmex XP-300 (ASTM). Fórmula de 3 partes: LYM / MXD / NEUT.
# MXD (mixed cells) NO es monocitos: no se mapea a MONO ni a EOS/BAS.
# Códigos MXD/MXD%/MXD# se omiten a propósito; la ingesta los ignora.
# NEUT_CAY no existe en el XP-300. MONO%/MONO solo aplican a 5 partes.
CODIGOS_SYSMEX_MXD: frozenset[str] = frozenset({"MXD", "MXD%", "MXD#"})

MAPEO_SYSMEX_XP300: dict[str, str] = {
    "WBC": "LEUCO",
    "RBC": "HEMATIES",
    "HGB": "HGB",
    "HB": "HGB",
    "HCT": "HTO",
    "HTO": "HTO",
    "MCV": "VCM",
    "MCHC": "CHCM",
    "RDW": "RDW",
    "RDW-CV": "RDW",
    "RDW-SD": "RDW",
    "PLT": "PLAQ",
    "NEUT%": "NEUT_SEG",
    "NEUT#": "NEUT_SEG",
    "NEUT": "NEUT_SEG",
    "LYM%": "LINF",
    "LYM#": "LINF",
    "LYM": "LINF",
    "EO%": "EOS",
    "EO": "EOS",
    "BA%": "BAS",
    "BA": "BAS",
    "MONO%": "MONO",
    "MONO": "MONO",
}

# Wiener CM260: códigos de canal típicos (editables; el lab los programa).
MAPEO_CM260: dict[str, str] = {
    "GLU": "GLU",
    "URE": "UREA",
    "UREA": "UREA",
    "CRE": "CREATI",
    "CREA": "CREATI",
    "CREATI": "CREATI",
    "AU": "AU",
    "UA": "AU",
    "CPK": "CPK",
    "CK": "CPK",
    "GOT": "GOT",
    "AST": "GOT",
    "GPT": "GPT",
    "ALT": "GPT",
    "FAL": "FAL",
    "ALP": "FAL",
    "BIL_D": "BIL_D",
    "DBIL": "BIL_D",
    "BIL_T": "BIL_T",
    "TBIL": "BIL_T",
    "COL": "COL_TOT",
    "COL_TOT": "COL_TOT",
    "CHOL": "COL_TOT",
    "HDL": "HDL",
    "TG": "TG",
    "TRIG": "TG",
    "FERR": "FERR",
    "FE": "FERR",
    "CF": "CF",
    "UIBC": "CF",
    "PROT_T": "PROT_T",
    "TP": "PROT_T",
    "ALB": "ALB",
    "CA": "CA",
    "MG": "MG",
    "P": "P",
    "PHOS": "P",
    "PCR_US": "PCR_US",
    "PCR": "PCR_US",
    "CRP": "PCR_US",
    "AMIL": "AMIL",
    "AMY": "AMIL",
    "LIP": "LIP",
    "LIPS": "LIP",
    "GGT": "GGT",
    "LDH": "LDH",
    "PROT_U_24": "PROT_U_24",
    "PROT_U_AZ": "PROT_U_AZ",
}

MAPEO_POR_DRIVER: dict[str, dict[str, str]] = {
    "CM260": MAPEO_CM260,
    "SYSMEX_XP300": MAPEO_SYSMEX_XP300,
}


def normalizar_codigo_analito(codigo: str | None) -> str:
    return (codigo or "").strip().upper()
