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
    "SANGRE_ERITRO": {"nombre": "Sangre eritro (VSG)", "color_tubo": "Negro"},
    "SANGRE_CITRATO_VSG": {"nombre": "Sangre citrato VSG (legacy)", "color_tubo": "Negro"},
    "SANGRE_HEPARINA": {"nombre": "Sangre heparina", "color_tubo": "Verde"},
    "SANGRE_HEPARINA_ART": {"nombre": "Sangre heparina arterial", "color_tubo": "Verde"},
    "SANGRE_HEPARINA_VEN": {"nombre": "Sangre heparina venosa", "color_tubo": "Verde"},
    "PLASMA_HEPARINA": {"nombre": "Plasma heparina (legacy)", "color_tubo": "Verde"},
    "MATERIA_FECAL": {"nombre": "Materia fecal", "color_tubo": "Frasco"},
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
    {"codigo": "HCM", "nombre": "Hemoglobina corpuscular media", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "HCM"},
    {"codigo": "RDW", "nombre": "RDW", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "RDW"},
    {"codigo": "LEUCO", "nombre": "Leucocitos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "GB"},
    {"codigo": "NEUT_CAY", "nombre": "Neutrófilos cayados", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "NEUT_SEG", "nombre": "Neutrófilos segmentados", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "EOS", "nombre": "Eosinófilos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "BAS", "nombre": "Basófilos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "LINF", "nombre": "Linfocitos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "MONO", "nombre": "Monocitos", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "PLAQ", "nombre": "Plaquetas", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO", "abreviatura": "Plaq"},
    # —— Perfil lipídico —— suero (rutina)
    {"codigo": "COL_TOT", "nombre": "Colesterol total", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "COL"},
    {"codigo": "HDL", "nombre": "HDL colesterol", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "HDL"},
    {"codigo": "LDL", "nombre": "LDL colesterol", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "LDL"},
    {"codigo": "COL_NO_LDL", "nombre": "Colesterol no-HDL", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "TG", "nombre": "Triglicéridos", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "TG"},
    {"codigo": "VLDL", "nombre": "Colesterol VLDL", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "VLDL"},
    {"codigo": "COL_RESID", "nombre": "Colesterol residual", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "RATIO_CT_HDL", "nombre": "Relación colesterol total/HDL", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    # —— Hepatograma —— suero (rutina)
    {"codigo": "GOT", "nombre": "GOT (AST)", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "GOT"},
    {"codigo": "GPT", "nombre": "GPT (ALT)", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "GPT"},
    {"codigo": "FAL", "nombre": "Fosfatasa alcalina", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "FA"},
    {"codigo": "BIL_T", "nombre": "Bilirrubina total", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "BIL_D", "nombre": "Bilirrubina directa", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "BIL_I", "nombre": "Bilirrubina indirecta", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    # —— Ionograma —— suero (rutina)
    {"codigo": "NA", "nombre": "Sodio", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "Na"},
    {"codigo": "K", "nombre": "Potasio", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "K"},
    {"codigo": "CL", "nombre": "Cloro", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "Cl"},
    # —— Coagulograma —— plasma citrato (no suero)
    {"codigo": "TP", "nombre": "Tiempo de protrombina", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "TP"},
    {"codigo": "PP", "nombre": "Porcentaje de protrombina", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "%PT"},
    {"codigo": "INR", "nombre": "R.I.N.", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "INR"},
    {"codigo": "KPTT", "nombre": "KPTT", "muestra": "PLASMA_CITRATO", "tipo_resultado": "NUMERICO", "abreviatura": "KPTT"},
    # —— Perfil férrico —— medidos: FERR, UIBC, FERRIT; calculados: CF, SAT_FE, TRANS
    {"codigo": "FERR", "nombre": "Ferremia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "UIBC", "nombre": "UIBC", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "UIBC"},
    {"codigo": "FERRIT", "nombre": "Ferritina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CF", "nombre": "Capacidad total de fijación", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "TIBC"},
    {"codigo": "SAT_FE", "nombre": "% de saturación de transferrina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "TRANS", "nombre": "Transferrina", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    # —— Orina completa ——
    {"codigo": "ORI_COLOR", "nombre": "Color (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_ASP", "nombre": "Aspecto (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
    {"codigo": "ORI_DENS", "nombre": "Densidad (orina)", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "ORI_PH", "nombre": "pH (orina)", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    # Reacciones de tira: se cargan como Negativo / - / + / ++ / +++ (CUALITATIVO)
    {"codigo": "ORI_GLU", "nombre": "Glucosa (orina)", "muestra": "ORINA", "tipo_resultado": "CUALITATIVO"},
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
    {
        "codigo": "ELP_AG",
        "nombre": "Relación albúmina/globulina",
        "muestra": "SUERO",
        "tipo_resultado": "NUMERICO",
        "abreviatura": "A/G",
    },
    {"codigo": "ELP_CONC", "nombre": "Conclusiones (proteinograma)", "muestra": "SUERO", "tipo_resultado": "TEXTO"},
    # —— Clearance / microalbuminuria / proteinuria 24 hs ——
    {"codigo": "CREA_U", "nombre": "Creatininuria", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "DIUR", "nombre": "Diuresis", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    {"codigo": "CLEAR_CREA", "nombre": "Clearance de creatinina", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    {"codigo": "MICROALB", "nombre": "Microalbuminuria", "muestra": "ORINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "MICROALB_24", "nombre": "Microalbuminuria 24 hs", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    # RAC (mg/g) = (MICROALB mg/L ÷ CREA_U mg/dL) × 100
    {
        "codigo": "RAC",
        "nombre": "RAC - Relación albúmina/creatinina",
        "muestra": "ORINA",
        "tipo_resultado": "NUMERICO",
        "abreviatura": "RAC",
    },
    # Ionograma urinario 24 hs (calculados desde concentración × diuresis)
    {"codigo": "NA_U24", "nombre": "Sodio urinario 24 hs", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO", "abreviatura": "Na u 24h"},
    {"codigo": "K_U24", "nombre": "Potasio urinario 24 hs", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO", "abreviatura": "K u 24h"},
    {"codigo": "CL_U24", "nombre": "Cloro urinario 24 hs", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO", "abreviatura": "Cl u 24h"},
    # Proteinuria: concentración del equipo (mg/dL) → PROT_U_24 calculado (mg/24 hs)
    {"codigo": "PROT_U_EQ", "nombre": "Proteinuria (concentración)", "muestra": "ORINA_24_H", "tipo_resultado": "NUMERICO"},
    # —— Exámenes sueltos del formulario (no panel) ——
    {"codigo": "HBA1C", "nombre": "Hemoglobina glicosilada (HbA1c)", "muestra": "SANGRE_EDTA", "tipo_resultado": "NUMERICO"},
    {"codigo": "GLU", "nombre": "Glucemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "UREA", "nombre": "Uremia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CREATI", "nombre": "Creatininemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "Cr"},
    {"codigo": "AU", "nombre": "Uricemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CA", "nombre": "Calcemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "MG", "nombre": "Magnesemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "P", "nombre": "Fosfatemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "CA_ION", "nombre": "Calcio iónico", "muestra": "SANGRE_HEPARINA", "tipo_resultado": "NUMERICO"},
    {"codigo": "PROT_T", "nombre": "Proteinemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "ALB", "nombre": "Albuminemia", "muestra": "SUERO", "tipo_resultado": "NUMERICO"},
    {"codigo": "VSG", "nombre": "Eritrosedimentación (VSG)", "muestra": "SANGRE_ERITRO", "tipo_resultado": "NUMERICO"},
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
    # —— Pruebas rápidas / sueltos frecuentes (formulario debajo de LDH) ——
    {"codigo": "HBVAGS", "nombre": "Test rápido HBsAg (Hepatitis B)", "muestra": "SUERO", "tipo_resultado": "CUALITATIVO", "abreviatura": "HBsAg"},
    {"codigo": "HCVG", "nombre": "Test rápido Hepatitis C", "muestra": "SUERO", "tipo_resultado": "CUALITATIVO", "abreviatura": "HCV"},
    {"codigo": "HIVAC", "nombre": "Test rápido HIV", "muestra": "SUERO", "tipo_resultado": "CUALITATIVO", "abreviatura": "HIV"},
    {"codigo": "VDRL", "nombre": "VDRL", "muestra": "SUERO", "tipo_resultado": "CUALITATIVO", "abreviatura": "VDRL"},
    {"codigo": "HCGB", "nombre": "Gonadotrofina coriónica (β-HCG / embarazo)", "muestra": "SUERO", "tipo_resultado": "CUALITATIVO", "abreviatura": "βHCG"},
    {"codigo": "SANOC", "nombre": "Sangre oculta en materia fecal", "muestra": "MATERIA_FECAL", "tipo_resultado": "CUALITATIVO", "abreviatura": "SOMF"},
    {"codigo": "ASTO", "nombre": "ASTO (Antiestreptolisina O)", "muestra": "SUERO", "tipo_resultado": "NUMERICO", "abreviatura": "ASTO"},
    {"codigo": "GRUPO", "nombre": "Grupo sanguíneo", "muestra": "SANGRE_EDTA", "tipo_resultado": "CUALITATIVO", "abreviatura": "GS"},
    # —— FiO2 compartido (contexto clínico; no genera tubo propio) ——
    {"codigo": "FIO2", "nombre": "FiO2", "muestra": "SANGRE_HEPARINA", "tipo_resultado": "NUMERICO", "abreviatura": "FiO2"},
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
    # —— ENA (panel PAN_ENA): un resultado por antígeno ——
    {
        "codigo": "ENA_RO52",
        "nombre": "SSA/Ro52 (TRIM21) Ac.",
        "muestra": "SUERO",
        "tipo_resultado": "TEXTO",
        "abreviatura": "Ro52",
    },
    {
        "codigo": "ENA_RO60",
        "nombre": "SSA/Ro60 Ac.",
        "muestra": "SUERO",
        "tipo_resultado": "TEXTO",
        "abreviatura": "Ro60",
    },
    {
        "codigo": "ENA_SSB",
        "nombre": "SSB/La Ac.",
        "muestra": "SUERO",
        "tipo_resultado": "TEXTO",
        "abreviatura": "SSB",
    },
    {
        "codigo": "ENA_RNP",
        "nombre": "RNP Ac.",
        "muestra": "SUERO",
        "tipo_resultado": "TEXTO",
        "abreviatura": "RNP",
    },
    {
        "codigo": "ENA_SM",
        "nombre": "Sm Ac.",
        "muestra": "SUERO",
        "tipo_resultado": "TEXTO",
        "abreviatura": "Sm",
    },
]

# Códigos legacy del seed demo que se reemplazan por panel + componentes
LEGACY_CODIGOS_DESACTIVAR = frozenset({"HEMO", "COL", "HEM", "COA", "EAB_ART", "EAB_VEN", "ENA"})

# Pedido legacy ENA (un solo código) → panel con un resultado por antígeno
LEGACY_EXAMEN_A_PANEL: dict[str, str] = {
    "ENA": "PAN_ENA",
}

# Componentes EAB (jeringas art/ven). FIO2 es compartido entre ambos paneles.
COMPONENTES_EAB_ART: list[str] = [
    "FIO2", "PH_ART", "PO2_ART", "PCO2_ART", "SAT_O2_ART", "HCO3_ART", "BE_ART",
]
COMPONENTES_EAB_VEN: list[str] = [
    "FIO2", "PH_VEN", "PO2_VEN", "PCO2_VEN", "SAT_O2_VEN", "HCO3_VEN", "BE_VEN",
]

COMPONENTES_ENA: list[str] = [
    "ENA_RO52",
    "ENA_RO60",
    "ENA_SSB",
    "ENA_RNP",
    "ENA_SM",
]

# ---------------------------------------------------------------------------
# Paneles prioritarios + nombres alineados al papel
# ---------------------------------------------------------------------------

PANELES: list[PanelDef] = [
    {
        "codigo": "PAN_HEMO",
        "nombre": "Hemograma",
        "componentes": [
            "HEMATIES", "HTO", "HGB", "RDW", "VCM", "HCM", "CHCM", "PLAQ", "LEUCO",
            "NEUT_CAY", "NEUT_SEG", "EOS", "BAS", "LINF", "MONO",
        ],
    },
    {
        "codigo": "PAN_LIP",
        "nombre": "Perfil lipídico",
        "componentes": [
            "COL_TOT", "LDL", "VLDL", "HDL", "TG", "COL_NO_LDL", "COL_RESID", "RATIO_CT_HDL",
        ],
    },
    {
        "codigo": "PAN_HEP",
        "nombre": "Hepatograma",
        "componentes": ["GOT", "GPT", "FAL", "BIL_T", "BIL_D", "BIL_I"],
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
        "componentes": ["FERR", "UIBC", "FERRIT", "CF", "SAT_FE", "TRANS"],
    },
    {
        "codigo": "PAN_ORI",
        "nombre": "Orina completa",
        "componentes": [
            "ORI_COLOR", "ORI_ASP", "ORI_DENS", "ORI_PH", "ORI_GLU", "ORI_BIL",
            "ORI_NIT", "ORI_CET", "ORI_CEL", "ORI_LEU", "ORI_HEM", "ORI_PIO",
            "ORI_MUC", "ORI_CRIS", "ORI_CONC",
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
        "componentes": ["NA_U", "K_U", "CL_U", "DIUR", "NA_U24", "K_U24", "CL_U24"],
    },
    {
        "codigo": "PAN_ELP",
        "nombre": "Proteinograma electroforético",
        "componentes": [
            "PROT_T",
            "ELP_ALB",
            "ELP_A1",
            "ELP_A2",
            "ELP_B1",
            "ELP_B2",
            "ELP_GAM",
            "ELP_AG",
            "ELP_CONC",
        ],
    },
    {
        "codigo": "PAN_CLEAR",
        "nombre": "Clearance de creatinina",
        "componentes": ["CREATI", "CREA_U", "DIUR", "CLEAR_CREA"],
    },
    {
        "codigo": "PAN_MALB24",
        "nombre": "Microalbuminuria 24 hs",
        "componentes": ["MICROALB", "DIUR", "MICROALB_24"],
    },
    {
        "codigo": "PAN_MALB_AZ",
        "nombre": "Microalbuminuria al azar",
        "componentes": ["MICROALB", "CREA_U", "RAC"],
    },
    {
        "codigo": "PAN_PROT24",
        "nombre": "Proteinuria 24 hs",
        "componentes": ["PROT_U_EQ", "DIUR", "PROT_U_24"],
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
    {
        "codigo": "PAN_ENA",
        "nombre": "ENA - Antígenos nucleares extraíbles Ac.IgG",
        "componentes": list(COMPONENTES_ENA),
    },
]

# Exámenes sueltos solicitables (aparecen en el papel fuera de paneles)
EXAMENES_SUELTOS_PDF: list[str] = [
    "HBA1C", "GLU", "UREA", "CREATI", "AU", "CA", "MG", "P", "CL", "CA_ION",
    "PROT_T", "ALB", "INR", "VSG", "PCR_US", "AMIL", "LIP", "GGT", "LDH",
    "CPK", "CPK_MB", "TROP_I", "TROP_US", "MIOG", "PROBNP", "DDIM",
    "PROT_U_AZ", "LPA", "PSA", "TSH", "T3", "T4", "T4L",
    "B12", "VITD", "LACT",
    "HBVAGS", "HCVG", "HIVAC", "VDRL", "GRUPO",
]

# Orden de lectura del formulario «Solicitud de análisis» (fila a fila, izq → der).
# Debe coincidir con frontend `SOLICITUD_ANALISIS_PAPEL_ROWS`.
# NO usar para talón / carga de resultados: ver ORDEN_PRESENTACION_PEDIDO.
ORDEN_FORMULARIO_PAPEL: list[str] = [
    "PAN_HEMO", "CPK",
    "HBA1C", "CPK_MB",
    "GLU", "TROP_I",
    "UREA", "MIOG",
    "CREATI", "TROP_US",
    "AU", "PROBNP",
    "CA", "DDIM",
    "MG", "PAN_ORI",
    "P", "PAN_CLEAR",
    "PAN_FERR", "PAN_IONO_U24",
    "PAN_IONO", "PAN_IONO_U",
    "CL", "PAN_PROT24",
    "CA_ION", "PROT_U_AZ",
    "PAN_LIP", "PAN_MALB24",
    "PAN_HEP", "PAN_MALB_AZ",
    "PROT_T", "PAN_ELP",
    "ALB", "LPA",
    "PAN_COAG", "PSA",
    "INR", "TSH",
    "VSG", "T3",
    "PCR_US", "T4",
    "AMIL", "T4L",
    "LIP", "B12",
    "GGT", "VITD",
    "LDH", "PAN_EAB_ART",
    "HBVAGS", "PAN_EAB_VEN",
    "HCVG", "LACT",
    "HIVAC",
    "VDRL",
    "GRUPO",
]

# Orden de presentación: talón PDF, carga de resultados e informe.
# Paneles = un ítem; componentes del panel no se duplican como sueltos.
# Orinas van al final (PAN_ORI última) vía lógica en orden_grupos_informe / talón.
# Debe coincidir con frontend `ORDEN_PRESENTACION_PEDIDO` en limsOrdenInforme.ts.
ORDEN_PRESENTACION_PEDIDO: list[str] = [
    "PAN_HEMO",
    # Química CM260 sueltos (CPK y orinas fuera de este bloque)
    "GLU",
    "UREA",
    "CREATI",
    # Clearance (mixto suero+orina): junto a creatininemia en informe/carga
    "PAN_CLEAR",
    "AU",
    "CA",
    "MG",
    "P",
    "PROT_T",
    "ALB",
    "FERR",
    "UIBC",
    "GOT",
    "GPT",
    "FAL",
    "BIL_T",
    "BIL_D",
    "BIL_I",
    "COL_TOT",
    "HDL",
    "TG",
    "LDL",
    "VLDL",
    "PCR_US",
    "AMIL",
    "LIP",
    "GGT",
    "LDH",
    "PAN_HEP",
    "PAN_LIP",
    "PAN_IONO",
    "CPK",
    "CPK_MB",
    "TROP_I",
    "TROP_US",
    "MIOG",
    "PAN_ENA",
]
