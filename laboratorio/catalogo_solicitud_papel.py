"""
Catálogo LIMS alineado al formulario en papel «Solicitud de análisis».

Cada analito existe una sola vez como ``TipoExamen``; los paneles referencian
componentes vía M2M sin duplicar registros.
"""

from __future__ import annotations

from typing import TypedDict


class ExamenDef(TypedDict, total=False):
    codigo: str
    nombre: str
    muestra: str
    tipo_resultado: str
    abreviatura: str


class PanelDef(TypedDict):
    codigo: str
    nombre: str
    componentes: list[str]


MUESTRAS: dict[str, dict[str, str]] = {
    "SANGRE": {"nombre": "Sangre (Suero)", "color_tubo": "Rojo"},
    "ORINA": {"nombre": "Orina", "color_tubo": "Frasco estéril"},
}

# ---------------------------------------------------------------------------
# Exámenes individuales (códigos únicos)
# ---------------------------------------------------------------------------

EXAMENES: list[ExamenDef] = [
    # —— Hemograma (panel) ——
    {"codigo": "HEMATIES", "nombre": "Hematíes", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "Ht"},
    {"codigo": "HTO", "nombre": "Hematocrito (RW)", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "RW"},
    {"codigo": "HGB", "nombre": "Hemoglobina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "Hb"},
    {"codigo": "RDW", "nombre": "RDW", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "RDW"},
    {"codigo": "LEU", "nombre": "Leucocitos", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "GB"},
    {"codigo": "NEUT_CAY", "nombre": "Neutrófilos cayados", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "NEUT_SEG", "nombre": "Neutrófilos segmentados", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "EOS", "nombre": "Eosinófilos", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "BAS", "nombre": "Basófilos", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "LINF", "nombre": "Linfocitos", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "MONO", "nombre": "Monocitos", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "PLAQ", "nombre": "Plaquetas", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "Plaq"},
    # —— Perfil lipídico ——
    {"codigo": "COL_TOT", "nombre": "Colesterol total", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "COL"},
    {"codigo": "HDL", "nombre": "HDL colesterol", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "HDL"},
    {"codigo": "LDL", "nombre": "LDL colesterol", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "LDL"},
    {"codigo": "COL_NO_LDL", "nombre": "Colesterol no LDL", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "TG", "nombre": "Triglicéridos", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "TG"},
    # —— Hepatograma ——
    {"codigo": "GOT", "nombre": "GOT (AST)", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "GOT"},
    {"codigo": "GPT", "nombre": "GPT (ALT)", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "GPT"},
    {"codigo": "FAL", "nombre": "Fosfatasa alcalina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "FA"},
    {"codigo": "BIL_T", "nombre": "Bilirrubina total", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "BIL_D", "nombre": "Bilirrubina directa", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    # —— Ionograma plasmático ——
    {"codigo": "NA", "nombre": "Sodio", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "Na"},
    {"codigo": "K", "nombre": "Potasio", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "K"},
    {"codigo": "CL", "nombre": "Cloro", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "Cl"},
    # —— Coagulograma ——
    {"codigo": "TP", "nombre": "Tiempo de protrombina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "TP"},
    {"codigo": "PP", "nombre": "Porcentaje de protrombina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "%PT"},
    {"codigo": "INR", "nombre": "R.I.N.", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "INR"},
    {"codigo": "KPTT", "nombre": "KPTT", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "KPTT"},
    # —— Perfil férrico ——
    {"codigo": "CF", "nombre": "Capacidad de fijación", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "FERR", "nombre": "Ferremia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "TRANS", "nombre": "Transferrina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "FERRIT", "nombre": "Ferritina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "SAT_FE", "nombre": "% de saturación de transferrina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    # —— Orina completa ——
    {"codigo": "ORI_COLOR", "nombre": "Color (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_ASP", "nombre": "Aspecto (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_DENS", "nombre": "Densidad (orina)", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "ORI_PH", "nombre": "pH (orina)", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "ORI_BIL", "nombre": "Bilirrubina (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_NIT", "nombre": "Nitritos (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_CET", "nombre": "C. cetónicos (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_CEL", "nombre": "Células (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_LEU", "nombre": "Leucocitos (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_HEM", "nombre": "Hematíes (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_PIO", "nombre": "Piocitos (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_MUC", "nombre": "Mucus (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_CRIS", "nombre": "Cristales (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_CONC", "nombre": "Conclusión (orina completa)", "muestra": "ORINA", "tipo_resultado": "TEXTO"},
    # —— Ionograma urinario (compartido 24 hs / al azar) ——
    {"codigo": "NA_U", "nombre": "Sodio urinario", "muestra": "ORINA", "tipo_resultado": "NUMERICO", "abreviatura": "Na u"},
    {"codigo": "K_U", "nombre": "Potasio urinario", "muestra": "ORINA", "tipo_resultado": "NUMERICO", "abreviatura": "K u"},
    {"codigo": "CL_U", "nombre": "Cloro urinario", "muestra": "ORINA", "tipo_resultado": "NUMERICO", "abreviatura": "Cl u"},
    # —— Proteinograma electroforético ——
    {"codigo": "ELP_ALB", "nombre": "Albúmina (electroforesis)", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_A1", "nombre": "Alfa 1 globulina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_A2", "nombre": "Alfa 2 globulina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_B1", "nombre": "Beta 1 globulina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_B2", "nombre": "Beta 2 globulina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_GAM", "nombre": "Gamma globulina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_CONC", "nombre": "Conclusiones (proteinograma)", "muestra": "SANGRE", "tipo_resultado": "TEXTO"},
    # —— Clearance / microalbuminuria ——
    {"codigo": "CREA_U", "nombre": "Creatininuria", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "DIUR", "nombre": "Diuresis", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "CLEAR_CREA", "nombre": "Clearance de creatinina", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "MICROALB", "nombre": "Microalbuminuria", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    # —— Exámenes sueltos del formulario (no panel) ——
    {"codigo": "HBA1C", "nombre": "Hemoglobina glicosilada (HbA1c)", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "GLU", "nombre": "Glucemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "UREA", "nombre": "Uremia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "CREA", "nombre": "Creatininemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "AU", "nombre": "Uricemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "CA", "nombre": "Calcemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "MG", "nombre": "Magnesemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "P", "nombre": "Fosfatemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "CA_ION", "nombre": "Calcio iónico", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_T", "nombre": "Proteinemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "ALB", "nombre": "Albuminemia", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "VSG", "nombre": "Eritrosedimentación (VSG)", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "PCR_US", "nombre": "Proteína C reactiva ultrasensible", "muestra": "SANGRE", "tipo_resultado": "NUMERICO", "abreviatura": "PCR-us"},
    {"codigo": "AMIL", "nombre": "Amilasa", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "LIP", "nombre": "Lipasa", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "GGT", "nombre": "GGT", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "LDH", "nombre": "LDH", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "CPK", "nombre": "CPK", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "CPK_MB", "nombre": "CPK-MB", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "TROP_I", "nombre": "Troponina I", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "TROP_US", "nombre": "Troponina I ultrasensible", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "MIOG", "nombre": "Mioglobina", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROBNP", "nombre": "Pro-BNP", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "DDIM", "nombre": "Dímero D", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_U_24", "nombre": "Proteinuria 24 hs", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_U_AZ", "nombre": "Proteinuria al azar", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "LPA", "nombre": "Lipoproteína A", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "PSA", "nombre": "PSA", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "TSH", "nombre": "TSH", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "T3", "nombre": "T3", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "T4", "nombre": "T4", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "T4L", "nombre": "T4 libre", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "B12", "nombre": "Vitamina B12", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "VITD", "nombre": "Vitamina D", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
    {"codigo": "EAB_ART", "nombre": "EAB arterial", "muestra": "SANGRE", "tipo_resultado": "TEXTO"},
    {"codigo": "EAB_VEN", "nombre": "EAB venoso", "muestra": "SANGRE", "tipo_resultado": "TEXTO"},
    {"codigo": "LACT", "nombre": "Ácido láctico / Lactato", "muestra": "SANGRE", "tipo_resultado": "NUMERICO"},
]

# Códigos legacy del seed demo que se reemplazan por panel + componentes
LEGACY_CODIGOS_DESACTIVAR = frozenset({"HEMO", "COL"})

# ---------------------------------------------------------------------------
# 14 paneles prioritarios + nombres alineados al papel
# ---------------------------------------------------------------------------

PANELES: list[PanelDef] = [
    {
        "codigo": "PAN_HEMO",
        "nombre": "Hemograma",
        "componentes": [
            "HEMATIES", "HTO", "HGB", "RDW", "LEU", "NEUT_CAY", "NEUT_SEG",
            "EOS", "BAS", "LINF", "MONO", "PLAQ",
        ],
    },
    {
        "codigo": "PAN_LIP",
        "nombre": "Perfil lipídico",
        "componentes": ["COL_TOT", "HDL", "LDL", "COL_NO_LDL", "TG"],
    },
    {
        "codigo": "PAN_HEP",
        "nombre": "Hepatograma",
        "componentes": ["GOT", "GPT", "FAL", "BIL_T", "BIL_D"],
    },
    {
        "codigo": "PAN_IONO",
        "nombre": "Ionograma plasmático",
        "componentes": ["NA", "K", "CL"],
    },
    {
        "codigo": "PAN_COAG",
        "nombre": "Coagulograma básico",
        "componentes": ["TP", "PP", "INR", "KPTT"],
    },
    {
        "codigo": "PAN_FERR",
        "nombre": "Perfil férrico",
        "componentes": ["CF", "FERR", "TRANS", "FERRIT", "SAT_FE"],
    },
    {
        "codigo": "PAN_ORI",
        "nombre": "Orina completa",
        "componentes": [
            "ORI_COLOR", "ORI_ASP", "ORI_DENS", "ORI_PH", "ORI_BIL", "ORI_NIT",
            "ORI_CET", "ORI_CEL", "ORI_LEU", "ORI_HEM", "ORI_PIO", "ORI_MUC",
            "ORI_CRIS", "ORI_CONC",
        ],
    },
    {
        "codigo": "PAN_IONO_U",
        "nombre": "Ionograma urinario al azar",
        "componentes": ["NA_U", "K_U", "CL_U"],
    },
    {
        "codigo": "PAN_IONO_U24",
        "nombre": "Ionograma urinario 24 hs",
        "componentes": ["NA_U", "K_U", "CL_U"],
    },
    {
        "codigo": "PAN_ELP",
        "nombre": "Proteinograma electroforético",
        "componentes": ["ELP_ALB", "ELP_A1", "ELP_A2", "ELP_B1", "ELP_B2", "ELP_GAM", "ELP_CONC"],
    },
    {
        "codigo": "PAN_CLEAR",
        "nombre": "Clearance de creatinina",
        "componentes": ["CREA", "CREA_U", "DIUR", "CLEAR_CREA"],
    },
    {
        "codigo": "PAN_MALB24",
        "nombre": "Microalbuminuria 24 hs",
        "componentes": ["MICROALB", "DIUR"],
    },
    {
        "codigo": "PAN_MALB_AZ",
        "nombre": "Microalbuminuria al azar",
        "componentes": ["MICROALB", "CREA_U"],
    },
]

# Exámenes sueltos solicitables (aparecen en el papel fuera de paneles)
EXAMENES_SUELTOS_PDF: list[str] = [
    "HBA1C", "GLU", "UREA", "CREA", "AU", "CA", "MG", "P", "CA_ION",
    "PROT_T", "ALB", "VSG", "PCR_US", "AMIL", "LIP", "GGT", "LDH",
    "CPK", "CPK_MB", "TROP_I", "TROP_US", "MIOG", "PROBNP", "DDIM",
    "PROT_U_24", "PROT_U_AZ", "LPA", "PSA", "TSH", "T3", "T4", "T4L",
    "B12", "VITD", "EAB_ART", "EAB_VEN", "LACT",
]
