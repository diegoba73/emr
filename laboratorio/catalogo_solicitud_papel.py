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
    "SUERO": {"nombre": "Suero", "color_tubo": "Rojo"},
    "ORINA": {"nombre": "Orina", "color_tubo": "Frasco estéril"},
    "ORINA_24_H": {"nombre": "Orina 24 hs", "color_tubo": "Bidón"},
    "SANGRE_EDTA": {"nombre": "Sangre EDTA", "color_tubo": "Morado"},
    "PLASMA_CITRATO": {"nombre": "Plasma citrato", "color_tubo": "Celeste"},
    "SANGRE_CITRATO_VSG": {"nombre": "Sangre citrato VSG", "color_tubo": "Negro"},
    "SANGRE_HEPARINA": {"nombre": "Sangre heparina", "color_tubo": "Verde"},
    "SANGRE_HEPARINA_ART": {"nombre": "Sangre heparina arterial", "color_tubo": "Verde"},
    "SANGRE_HEPARINA_VEN": {"nombre": "Sangre heparina venosa", "color_tubo": "Verde"},
    "PLASMA_HEPARINA": {"nombre": "Plasma heparina", "color_tubo": "Verde"},
}

# ---------------------------------------------------------------------------
# Exámenes individuales (códigos únicos)
# ---------------------------------------------------------------------------

EXAMENES: list[ExamenDef] = [
    # —— Hemograma (panel) —— sangre total EDTA (no suero)
    {"codigo": "HEMATIES", "nombre": "Hematíes", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "Ht"},
    {"codigo": "HTO", "nombre": "Hematocrito (RW)", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "RW"},
    {"codigo": "HGB", "nombre": "Hemoglobina", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "Hb"},
    {"codigo": "VCM", "nombre": "Volumen corpuscular medio", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "VCM"},
    {"codigo": "CHCM", "nombre": "Concentración de Hb corpuscular media", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "CHCM"},
    {"codigo": "RDW", "nombre": "RDW", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "RDW"},
    {"codigo": "LEUCO", "nombre": "Leucocitos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "GB"},
    {"codigo": "NEUT_CAY", "nombre": "Neutrófilos cayados", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "NEUT_SEG", "nombre": "Neutrófilos segmentados", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "EOS", "nombre": "Eosinófilos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "BAS", "nombre": "Basófilos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "LINF", "nombre": "Linfocitos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "MONO", "nombre": "Monocitos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "PLAQ", "nombre": "Plaquetas", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "Plaq"},
    # —— Perfil lipídico —— plasma heparina (rutina)
    {"codigo": "COL_TOT", "nombre": "Colesterol total", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "COL"},
    {"codigo": "HDL", "nombre": "HDL colesterol", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "HDL"},
    {"codigo": "LDL", "nombre": "LDL colesterol", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "LDL"},
    {"codigo": "COL_NO_LDL", "nombre": "Colesterol no LDL", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "TG", "nombre": "Triglicéridos", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "TG"},
    # —— Hepatograma —— plasma heparina (rutina)
    {"codigo": "GOT", "nombre": "GOT (AST)", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "GOT"},
    {"codigo": "GPT", "nombre": "GPT (ALT)", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "GPT"},
    {"codigo": "FAL", "nombre": "Fosfatasa alcalina", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "FA"},
    {"codigo": "BIL_T", "nombre": "Bilirrubina total", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "BIL_D", "nombre": "Bilirrubina directa", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO"},
    # —— Ionograma plasmático —— plasma heparina (rutina)
    {"codigo": "NA", "nombre": "Sodio", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "Na"},
    {"codigo": "K", "nombre": "Potasio", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "K"},
    {"codigo": "CL", "nombre": "Cloro", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "Cl"},
    # —— Coagulograma —— plasma citrato (no suero)
    {"codigo": "TP", "nombre": "Tiempo de protrombina", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "TP"},
    {"codigo": "PP", "nombre": "Porcentaje de protrombina", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "%PT"},
    {"codigo": "INR", "nombre": "R.I.N.", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "INR"},
    {"codigo": "KPTT", "nombre": "KPTT", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "KPTT"},
    # —— Perfil férrico ——
    {"codigo": "CF", "nombre": "Capacidad de fijación", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "FERR", "nombre": "Ferremia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "TRANS", "nombre": "Transferrina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "FERRIT", "nombre": "Ferritina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "SAT_FE", "nombre": "% de saturación de transferrina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
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
    {"codigo": "ELP_ALB", "nombre": "Albúmina (electroforesis)", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_A1", "nombre": "Alfa 1 globulina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_A2", "nombre": "Alfa 2 globulina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_B1", "nombre": "Beta 1 globulina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_B2", "nombre": "Beta 2 globulina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_GAM", "nombre": "Gamma globulina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ELP_CONC", "nombre": "Conclusiones (proteinograma)", "muestra": "SUERO", "tipo_resultado": "TEXTO"},
    # —— Clearance / microalbuminuria ——
    {"codigo": "CREA_U", "nombre": "Creatininuria", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "DIUR", "nombre": "Diuresis", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    {"codigo": "CLEAR_CREA", "nombre": "Clearance de creatinina", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    {"codigo": "MICROALB", "nombre": "Microalbuminuria", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    # —— Exámenes sueltos del formulario (no panel) ——
    {"codigo": "HBA1C", "nombre": "Hemoglobina glicosilada (HbA1c)", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "GLU", "nombre": "Glucemia", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "UREA", "nombre": "Uremia", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "CREATI", "nombre": "Creatininemia", "muestra": "PLASMA_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "Cr"},
    {"codigo": "AU", "nombre": "Uricemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CA", "nombre": "Calcemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "MG", "nombre": "Magnesemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "P", "nombre": "Fosfatemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CA_ION", "nombre": "Calcio iónico", "muestra": "SANGRE_HEPARINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_T", "nombre": "Proteinemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ALB", "nombre": "Albuminemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "VSG", "nombre": "Eritrosedimentación (VSG)", "muestra": "SANGRE_CITRATO_VSG", "tipo_resultado": "NUMERICO"},
    {"codigo": "PCR_US", "nombre": "Proteína C reactiva ultrasensible", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "PCR-us"},
    {"codigo": "AMIL", "nombre": "Amilasa", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "LIP", "nombre": "Lipasa", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "GGT", "nombre": "GGT", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "LDH", "nombre": "LDH", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CPK", "nombre": "CPK", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CPK_MB", "nombre": "CPK-MB", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "TROP_I", "nombre": "Troponina I", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "TROP_US", "nombre": "Troponina I ultrasensible", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "MIOG", "nombre": "Mioglobina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROBNP", "nombre": "Pro-BNP", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "DDIM", "nombre": "Dímero D", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_U_24", "nombre": "Proteinuria 24 hs", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_U_AZ", "nombre": "Proteinuria al azar", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "LPA", "nombre": "Lipoproteína A", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "PSA", "nombre": "PSA", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "TSH", "nombre": "TSH", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "T3", "nombre": "T3", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "T4", "nombre": "T4", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "T4L", "nombre": "T4 libre", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "B12", "nombre": "Vitamina B12", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "VITD", "nombre": "Vitamina D", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    # —— EAB arterial (panel PAN_EAB_ART) ——
    {"codigo": "PH_ART", "nombre": "pH (arterial)", "muestra": "SANGRE_HEPARINA_ART", "tipo_resultado": "NUMERICO", "abreviatura": "pH"},
    {"codigo": "PO2_ART", "nombre": "pO2 (arterial)", "muestra": "SANGRE_HEPARINA_ART", "tipo_resultado": "NUMERICO", "abreviatura": "pO2"},
    {"codigo": "PCO2_ART", "nombre": "pCO2 (arterial)", "muestra": "SANGRE_HEPARINA_ART", "tipo_resultado": "NUMERICO", "abreviatura": "pCO2"},
    {"codigo": "SAT_O2_ART", "nombre": "Sat. de O2 (arterial)", "muestra": "SANGRE_HEPARINA_ART", "tipo_resultado": "NUMERICO", "abreviatura": "SatO2"},
    {"codigo": "HCO3_ART", "nombre": "Bicarbonato (arterial)", "muestra": "SANGRE_HEPARINA_ART", "tipo_resultado": "NUMERICO", "abreviatura": "HCO3"},
    {"codigo": "BE_ART", "nombre": "Exceso de base (arterial)", "muestra": "SANGRE_HEPARINA_ART", "tipo_resultado": "NUMERICO", "abreviatura": "BE"},
    # —— EAB venoso (panel PAN_EAB_VEN) ——
    {"codigo": "PH_VEN", "nombre": "pH (venoso)", "muestra": "SANGRE_HEPARINA_VEN", "tipo_resultado": "NUMERICO", "abreviatura": "pH"},
    {"codigo": "PO2_VEN", "nombre": "pO2 (venoso)", "muestra": "SANGRE_HEPARINA_VEN", "tipo_resultado": "NUMERICO", "abreviatura": "pO2"},
    {"codigo": "PCO2_VEN", "nombre": "pCO2 (venoso)", "muestra": "SANGRE_HEPARINA_VEN", "tipo_resultado": "NUMERICO", "abreviatura": "pCO2"},
    {"codigo": "SAT_O2_VEN", "nombre": "Sat. de O2 (venoso)", "muestra": "SANGRE_HEPARINA_VEN", "tipo_resultado": "NUMERICO", "abreviatura": "SatO2"},
    {"codigo": "HCO3_VEN", "nombre": "Bicarbonato (venoso)", "muestra": "SANGRE_HEPARINA_VEN", "tipo_resultado": "NUMERICO", "abreviatura": "HCO3"},
    {"codigo": "BE_VEN", "nombre": "Exceso de base (venoso)", "muestra": "SANGRE_HEPARINA_VEN", "tipo_resultado": "NUMERICO", "abreviatura": "BE"},
    {"codigo": "LACT", "nombre": "Ácido láctico / Lactato", "muestra": "SANGRE_HEPARINA", "tipo_resultado": "NUMERICO"},
]

# Códigos legacy del seed demo que se reemplazan por panel + componentes
LEGACY_CODIGOS_DESACTIVAR = frozenset({"HEMO", "COL", "HEM", "COA", "EAB_ART", "EAB_VEN"})

# Componentes EAB (jeringas art/ven)
COMPONENTES_EAB_ART: list[str] = [
    "PH_ART", "PO2_ART", "PCO2_ART", "SAT_O2_ART", "HCO3_ART", "BE_ART",
]
COMPONENTES_EAB_VEN: list[str] = [
    "PH_VEN", "PO2_VEN", "PCO2_VEN", "SAT_O2_VEN", "HCO3_VEN", "BE_VEN",
]

# ---------------------------------------------------------------------------
# Paneles prioritarios + nombres alineados al papel
# ---------------------------------------------------------------------------

PANELES: list[PanelDef] = [
    {
        "codigo": "PAN_HEMO",
        "nombre": "Hemograma",
        "componentes": [
            "HEMATIES", "HTO", "HGB", "VCM", "CHCM", "RDW", "LEUCO", "NEUT_CAY",
            "NEUT_SEG", "EOS", "BAS", "LINF", "MONO", "PLAQ",
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
        "componentes": ["CREATI", "CREA_U", "DIUR", "CLEAR_CREA"],
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
    {
        "codigo": "PAN_EAB_ART",
        "nombre": "EAB arterial",
        "componentes": list(COMPONENTES_EAB_ART),
    },
    {
        "codigo": "PAN_EAB_VEN",
        "nombre": "EAB venoso",
        "componentes": list(COMPONENTES_EAB_VEN),
    },
]

# Exámenes sueltos solicitables (aparecen en el papel fuera de paneles)
EXAMENES_SUELTOS_PDF: list[str] = [
    "HBA1C", "GLU", "UREA", "CREATI", "AU", "CA", "MG", "P", "CA_ION",
    "PROT_T", "ALB", "VSG", "PCR_US", "AMIL", "LIP", "GGT", "LDH",
    "CPK", "CPK_MB", "TROP_I", "TROP_US", "MIOG", "PROBNP", "DDIM",
    "PROT_U_24", "PROT_U_AZ", "LPA", "PSA", "TSH", "T3", "T4", "T4L",
    "B12", "VITD", "LACT",
]
