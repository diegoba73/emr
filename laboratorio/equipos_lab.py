"""Equipos analíticos reales del lab y mapeo examen → equipo.

Fuente operativa para seed QC, gate IQC y UI. Códigos = TipoExamen.codigo canónicos.
"""
from __future__ import annotations

# Equipos físicos (codigo único EquipoAnalizador)
EQUIPOS_LAB: dict[str, dict[str, str]] = {
    "CM260": {
        "nombre": "Autoanalizador de química CM260",
        "marca_modelo": "CM260",
    },
    "SYSMEX_XP300": {
        "nombre": "Contador hematológico Sysmex XP-300",
        "marca_modelo": "Sysmex XP-300",
    },
    "COATRON": {
        "nombre": "Coagulómetro Coatron",
        "marca_modelo": "Coatron",
    },
    "DIESTRO": {
        "nombre": "Analizador de electrolitos Diestro",
        "marca_modelo": "Diestro",
    },
    "VIDAS_KUBE": {
        "nombre": "Inmunoensayo VIDAS KUBE",
        "marca_modelo": "bioMérieux VIDAS KUBE",
    },
    "EDAN_I15": {
        "nombre": "Gasometría EDAN i15",
        "marca_modelo": "EDAN i15",
    },
    "FINECARE": {
        "nombre": "Inmunoensayo Finecare",
        "marca_modelo": "Finecare",
    },
}

# Química CM260 — determinaciones reales del lab
EXAMENES_CM260: frozenset[str] = frozenset(
    {
        "GLU",
        "UREA",
        "CREATI",  # creatininemia (no CREA: alias IACA TFG)
        "AU",
        "CPK",
        "GOT",
        "GPT",
        "FAL",
        "BIL_D",
        "BIL_T",
        "COL_TOT",
        "HDL",
        "TG",
        "FERR",  # ferremia / hierro sérico
        "CF",  # capacidad de fijación (UIBC operativo)
        "PROT_T",
        "ALB",
        "CA",
        "MG",
        "P",
        "PCR_US",
        "AMIL",
        "LIP",
        "GGT",
        "LDH",
        "PROT_U_24",
        "PROT_U_AZ",
    }
)

# Hemograma Sysmex — componentes de PAN_HEMO
EXAMENES_SYSMEX: frozenset[str] = frozenset(
    {
        "HEMATIES",
        "HTO",
        "HGB",
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
    }
)

# Coagulograma Coatron
EXAMENES_COATRON: frozenset[str] = frozenset({"TP", "PP", "INR", "KPTT"})

# Ionograma Diestro
EXAMENES_DIESTRO: frozenset[str] = frozenset({"NA", "K", "CL", "CA_ION"})

# VIDAS KUBE — inmunoensayos
EXAMENES_VIDAS: frozenset[str] = frozenset(
    {"TROP_US", "TSH", "PSA", "T3", "T4", "T4L", "FERRIT"}
)

# Gasometría EDAN i15
EXAMENES_EDAN: frozenset[str] = frozenset(
    {
        "PH_ART",
        "PO2_ART",
        "PCO2_ART",
        "SAT_O2_ART",
        "HCO3_ART",
        "BE_ART",
        "PH_VEN",
        "PO2_VEN",
        "PCO2_VEN",
        "SAT_O2_VEN",
        "HCO3_VEN",
        "BE_VEN",
    }
)

# Finecare — POCT / cardíaco / otros
EXAMENES_FINECARE: frozenset[str] = frozenset(
    {
        "DDIM",
        "MICROALB",
        "HBA1C",
        "TROP_I",
        "CPK_MB",
        "MIOG",
    }
)

# codigo_equipo → códigos de examen
EXAMENES_POR_EQUIPO: dict[str, frozenset[str]] = {
    "CM260": EXAMENES_CM260,
    "SYSMEX_XP300": EXAMENES_SYSMEX,
    "COATRON": EXAMENES_COATRON,
    "DIESTRO": EXAMENES_DIESTRO,
    "VIDAS_KUBE": EXAMENES_VIDAS,
    "EDAN_I15": EXAMENES_EDAN,
    "FINECARE": EXAMENES_FINECARE,
}

# Invertido: codigo_examen → codigo_equipo
EXAMEN_A_EQUIPO: dict[str, str] = {
    codigo: equipo
    for equipo, codigos in EXAMENES_POR_EQUIPO.items()
    for codigo in codigos
}

# Equipos con control de producto multiparámetro (S1+S2 habilitan el equipo).
EQUIPOS_MULTIPARAM: frozenset[str] = frozenset(
    {"CM260", "SYSMEX_XP300", "COATRON", "DIESTRO", "EDAN_I15"}
)

# Equipos con material IQC por ensayo (VIDAS / Finecare).
EQUIPOS_POR_ENSAYO: frozenset[str] = frozenset({"VIDAS_KUBE", "FINECARE"})

# Productos multiparámetro a seedear: codigo → meta
PRODUCTOS_MULTIPARAM: dict[str, dict[str, str]] = {
    "STANDATROL_SE": {
        "nombre": "Standatrol S-E 2 Niveles",
        "marca": "Wiener",
        "equipo": "CM260",
    },
    "CTRL_SYSMEX": {
        "nombre": "Control hematología Sysmex",
        "marca": "Sysmex",
        "equipo": "SYSMEX_XP300",
    },
    "CTRL_COATRON": {
        "nombre": "Control coagulación Coatron",
        "marca": "Coatron",
        "equipo": "COATRON",
    },
    "CTRL_DIESTRO": {
        "nombre": "Control electrolitos Diestro",
        "marca": "Diestro",
        "equipo": "DIESTRO",
    },
    "CTRL_EDAN": {
        "nombre": "Control gasometría EDAN",
        "marca": "EDAN",
        "equipo": "EDAN_I15",
    },
}

# Targets a seedear por producto (subset razonable; CM260 = toda la química).
TARGETS_POR_PRODUCTO: dict[str, frozenset[str]] = {
    "STANDATROL_SE": EXAMENES_CM260,
    "CTRL_SYSMEX": frozenset({"HGB", "PLAQ", "LEUCO", "HTO"}),
    "CTRL_COATRON": frozenset({"TP", "KPTT", "INR"}),
    "CTRL_DIESTRO": frozenset({"NA", "K", "CL"}),
    "CTRL_EDAN": frozenset({"PH_ART", "PCO2_ART", "PO2_ART", "HCO3_ART"}),
}

# Materiales por ensayo (solo VIDAS / Finecare).
IQC_MATERIALES_POR_EQUIPO: dict[str, frozenset[str]] = {
    "VIDAS_KUBE": EXAMENES_VIDAS,
    "FINECARE": EXAMENES_FINECARE,
}


def equipo_codigo_para_examen(codigo_examen: str) -> str | None:
    return EXAMEN_A_EQUIPO.get((codigo_examen or "").strip().upper())


# Códigos operativos que en prod no coinciden con el canónico (ej. HEMO vs SYSMEX_XP300).
ALIAS_CODIGO_EQUIPO: dict[str, str] = {
    "HEMO": "SYSMEX_XP300",
    "SYSMEX": "SYSMEX_XP300",
    "XP300": "SYSMEX_XP300",
    "VIDAS": "VIDAS_KUBE",
    "FINECARE": "FINECARE",
}


def codigo_equipo_canonico(codigo_equipo: str) -> str:
    c = (codigo_equipo or "").strip().upper()
    return ALIAS_CODIGO_EQUIPO.get(c, c)


def es_equipo_multiparam(codigo_equipo: str) -> bool:
    return codigo_equipo_canonico(codigo_equipo) in EQUIPOS_MULTIPARAM


def es_equipo_por_ensayo(codigo_equipo: str) -> bool:
    return codigo_equipo_canonico(codigo_equipo) in EQUIPOS_POR_ENSAYO
