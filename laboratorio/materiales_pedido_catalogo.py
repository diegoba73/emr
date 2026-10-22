"""
Catálogo SoT de «materiales de pedido» (lab clínico + micro asociada).

Cada material define TipoMuestra clínica, determinaciones/paneles propios
(códigos nuevos, editables vía seed → TipoExamen/PanelExamen) y, si aplica,
cultivo + muestra de microbiología.

No reutiliza códigos de suero/hemograma. Códigos ≤ 20 caracteres.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Contenedor físico para líquidos / secreciones / tejidos (aditivo).
CONTENEDOR_ESTERIL = "FRASCO_ESTERIL"

UiPreset = Literal["sangre", "orina", ""] | str

# ---------------------------------------------------------------------------
# Analitos reutilizables (prefijo corto → nombre / tipo / unidad)
# ---------------------------------------------------------------------------

AnalitoKey = str

ANALITOS: dict[AnalitoKey, dict[str, str]] = {
    "ASP": {"nombre": "Aspecto", "tipo_resultado": "CUALITATIVO", "unidad": ""},
    "COL": {"nombre": "Color", "tipo_resultado": "CUALITATIVO", "unidad": ""},
    "VISC": {"nombre": "Viscosidad", "tipo_resultado": "CUALITATIVO", "unidad": ""},
    "RBC": {
        "nombre": "Recuento de hematíes",
        "tipo_resultado": "NUMERICO",
        "unidad": "células/µL",
    },
    "NC": {
        "nombre": "Recuento de células nucleadas",
        "tipo_resultado": "NUMERICO",
        "unidad": "células/µL",
    },
    "RAN": {
        "nombre": "Recuento absoluto de neutrófilos",
        "tipo_resultado": "NUMERICO",
        "unidad": "células/µL",
    },
    "GLU": {"nombre": "Glucosa", "tipo_resultado": "NUMERICO", "unidad": "mg/dL"},
    "PROT": {
        "nombre": "Proteínas totales",
        "tipo_resultado": "NUMERICO",
        "unidad": "g/dL",
    },
    "ALB": {"nombre": "Albúmina", "tipo_resultado": "NUMERICO", "unidad": "g/dL"},
    "LDH": {"nombre": "LDH", "tipo_resultado": "NUMERICO", "unidad": "U/L"},
    "LACT": {"nombre": "Lactato", "tipo_resultado": "NUMERICO", "unidad": "mmol/L"},
    "PH": {"nombre": "pH", "tipo_resultado": "NUMERICO", "unidad": ""},
    "ADA": {"nombre": "ADA", "tipo_resultado": "NUMERICO", "unidad": "U/L"},
    "AMIL": {"nombre": "Amilasa", "tipo_resultado": "NUMERICO", "unidad": "U/L"},
    "TG": {"nombre": "Triglicéridos", "tipo_resultado": "NUMERICO", "unidad": "mg/dL"},
    "CHOL": {"nombre": "Colesterol", "tipo_resultado": "NUMERICO", "unidad": "mg/dL"},
    "QUIL": {
        "nombre": "Quilomicrones",
        "tipo_resultado": "CUALITATIVO",
        "unidad": "",
    },
    "HTO": {"nombre": "Hematocrito", "tipo_resultado": "NUMERICO", "unidad": "%"},
    "BILI": {"nombre": "Bilirrubina", "tipo_resultado": "NUMERICO", "unidad": "mg/dL"},
    "CREA": {"nombre": "Creatinina", "tipo_resultado": "NUMERICO", "unidad": "mg/dL"},
    "CRIS": {
        "nombre": "Búsqueda de cristales",
        "tipo_resultado": "CUALITATIVO",
        "unidad": "",
    },
    "CEA": {"nombre": "CEA", "tipo_resultado": "NUMERICO", "unidad": "ng/mL"},
    "CITOL": {
        "nombre": "Citología diagnóstica",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
    "HEMOS": {
        "nombre": "Búsqueda de hemosiderófagos",
        "tipo_resultado": "CUALITATIVO",
        "unidad": "",
    },
    "B2TR": {
        "nombre": "Beta-2 transferrina",
        "tipo_resultado": "CUALITATIVO",
        "unidad": "",
    },
    "BTRA": {
        "nombre": "Beta-traza",
        "tipo_resultado": "NUMERICO",
        "unidad": "mg/L",
    },
    "ESPM": {
        "nombre": "Espermograma",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
    "LEU": {
        "nombre": "Recuento de leucocitos",
        "tipo_resultado": "NUMERICO",
        "unidad": "células/µL",
    },
    "FRUC": {
        "nombre": "Fructosa seminal",
        "tipo_resultado": "NUMERICO",
        "unidad": "mg/dL",
    },
    "SOH": {
        "nombre": "Sangre oculta",
        "tipo_resultado": "CUALITATIVO",
        "unidad": "",
    },
    "CALP": {
        "nombre": "Calprotectina",
        "tipo_resultado": "NUMERICO",
        "unidad": "µg/g",
    },
    "ELAS": {
        "nombre": "Elastasa pancreática",
        "tipo_resultado": "NUMERICO",
        "unidad": "µg/g",
    },
    "GRAS": {
        "nombre": "Grasa fecal",
        "tipo_resultado": "NUMERICO",
        "unidad": "g/24h",
    },
    "UREA": {
        "nombre": "Prueba rápida de ureasa",
        "tipo_resultado": "CUALITATIVO",
        "unidad": "",
    },
    "CITO": {
        "nombre": "Citometría de flujo",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
    "MIEL": {"nombre": "Mielograma", "tipo_resultado": "TEXTO", "unidad": ""},
    "FE": {
        "nombre": "Tinción de hierro",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
    "CIGEN": {
        "nombre": "Citogenética",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
    "KARI": {"nombre": "Cariotipo", "tipo_resultado": "TEXTO", "unidad": ""},
    "CMA": {
        "nombre": "Microarreglo cromosómico",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
    "CL": {"nombre": "Cloruro", "tipo_resultado": "NUMERICO", "unidad": "mmol/L"},
    "CALC": {
        "nombre": "Análisis de composición del cálculo",
        "tipo_resultado": "TEXTO",
        "unidad": "",
    },
}

# Componentes del diferencial celular (%). Prefijos cortos ≠ hemograma.
DIFERENCIAL_COMPONENTES: list[tuple[str, str]] = [
    ("NEUT", "Neutrófilos"),
    ("LINF", "Linfocitos"),
    ("MOMA", "Monocitos/Macrófagos"),
    ("EOS", "Eosinófilos"),
    ("OTRA", "Otras células"),
]

# Orden de presentación dentro de cada material (no sangre/orina):
# físicos → estudios especiales → recuentos/diferencial/microscopia → químicos.
ANALITOS_FISICOS: tuple[str, ...] = ("ASP", "COL", "VISC", "PH")
ANALITOS_ESTUDIOS: tuple[str, ...] = (
    "ESPM",
    "MIEL",
    "FE",
    "CIGEN",
    "KARI",
    "CMA",
    "CALC",
)
ANALITOS_CELULARES: tuple[str, ...] = ("RBC", "NC", "LEU", "RAN", "HTO")
ANALITOS_MICROS: tuple[str, ...] = ("CRIS", "HEMOS", "CITOL", "CITO")
# Prefijos de códigos material (examenes + PAN_DIF + diferencial) para ranking UI/PDF.
PREFIJOS_ORDEN_MATERIAL: tuple[str, ...] = (
    *ANALITOS_FISICOS,
    *ANALITOS_ESTUDIOS,
    *ANALITOS_CELULARES,
    "PAN_DIF",
    *(p for p, _ in DIFERENCIAL_COMPONENTES),
    *ANALITOS_MICROS,
    "GLU",
    "PROT",
    "ALB",
    "LDH",
    "LACT",
    "ADA",
    "AMIL",
    "TG",
    "CHOL",
    "QUIL",
    "BILI",
    "CREA",
    "CEA",
    "B2TR",
    "BTRA",
    "FRUC",
    "SOH",
    "CALP",
    "ELAS",
    "GRAS",
    "UREA",
    "CL",
)
_PREFIJO_ORDEN_RANK: dict[str, int] = {
    p: i for i, p in enumerate(PREFIJOS_ORDEN_MATERIAL)
}
_PREFIJOS_MATCH_ORDEN: tuple[str, ...] = tuple(
    sorted(PREFIJOS_ORDEN_MATERIAL, key=len, reverse=True)
)

CelularFlag = Literal["rbc", "nc", "dif", "citol"]


@dataclass(frozen=True)
class MaterialPedidoDef:
    codigo: str
    nombre: str
    sufijo: str
    """Códigos de analito (claves ANALITOS) además del bloque celular."""
    analitos: tuple[str, ...] = ()
    celular: frozenset[CelularFlag] = frozenset()
    cultivo_micro: str | None = None
    muestra_micro: str | None = None
    color_tubo: str = "Transparente"
    """Preset UI especial: sangre/orina usan grillas legacy; vacío = grilla desde catálogo."""
    ui_preset: str = ""
    tipo_muestra_codigos_extra: tuple[str, ...] = ()
    """Si True, aparece al abrir el selector sin tipear (además del default Sangre)."""
    frecuente: bool = False


def _cel(*flags: CelularFlag) -> frozenset[CelularFlag]:
    return frozenset(flags)


def _code(prefix: str, sufijo: str) -> str:
    c = f"{prefix}_{sufijo}"
    if len(c) > 20:
        raise ValueError(f"Código demasiado largo ({len(c)}): {c}")
    return c


# ---------------------------------------------------------------------------
# Tabla de materiales (plan + tabla del usuario)
# ---------------------------------------------------------------------------

MATERIALES_PEDIDO: tuple[MaterialPedidoDef, ...] = (
    MaterialPedidoDef(
        codigo="SANGRE",
        nombre="Sangre",
        sufijo="SG",
        ui_preset="sangre",
        cultivo_micro="HEMOCULTIVO",
        muestra_micro="SANGRE",
        # Canónicos; la API amplia con toda variante sangre/suero/plasma (ver as_api_list).
        tipo_muestra_codigos_extra=(
            "SUERO",
            "SANGRE_EDTA",
            "PLASMA_CITRATO",
            "PLASMA_EDTA",
            "SANGRE_ERITRO",
            "SANGRE_CITRATO_VSG",
            "SANGRE_HEPARINA",
            "SANGRE_HEPARINA_ART",
            "SANGRE_HEPARINA_VEN",
            "PLASMA_HEPARINA",
        ),
    ),
    MaterialPedidoDef(
        codigo="ORINA",
        nombre="Orina",
        sufijo="U",
        ui_preset="orina",
        cultivo_micro="UROCULTIVO",
        muestra_micro="ORINA",
        tipo_muestra_codigos_extra=("ORINA", "ORINA_24_H"),
        frecuente=True,
    ),
    MaterialPedidoDef(
        codigo="LCR",
        nombre="Líquido cefalorraquídeo (LCR)",
        sufijo="LCR",
        analitos=("ASP", "COL", "GLU", "PROT", "LACT"),
        celular=_cel("rbc", "nc", "dif", "citol"),
        cultivo_micro="LCR",
        muestra_micro="LCR",
    ),
    MaterialPedidoDef(
        codigo="LIQ_PLEURAL",
        nombre="Líquido pleural",
        sufijo="PLE",
        analitos=(
            "ASP",
            "COL",
            "PH",
            "HTO",
            "PROT",
            "ALB",
            "LDH",
            "GLU",
            "ADA",
            "AMIL",
            "TG",
            "CHOL",
            "QUIL",
        ),
        celular=_cel("rbc", "nc", "dif", "citol"),
        cultivo_micro="LIQUIDO_PLEURAL",
        muestra_micro="LIQUIDO_PLEURAL",
    ),
    MaterialPedidoDef(
        codigo="LIQ_ASCITICO",
        nombre="Líquido ascítico",
        sufijo="ASC",
        analitos=(
            "ASP",
            "COL",
            "RAN",
            "ALB",
            "PROT",
            "GLU",
            "LDH",
            "AMIL",
            "TG",
            "ADA",
            "BILI",
            "CREA",
        ),
        celular=_cel("rbc", "nc", "dif", "citol"),
        cultivo_micro="LIQUIDO_ASCITICO",
        muestra_micro="LIQUIDO_ASCITICO",
    ),
    MaterialPedidoDef(
        codigo="LIQ_PERITON",
        nombre="Líquido peritoneal",
        sufijo="PER",
        analitos=("ASP", "COL", "GLU", "PROT", "ALB", "LDH"),
        celular=_cel("rbc", "nc", "dif", "citol"),
        cultivo_micro="LIQUIDO_PERITONEAL",
        muestra_micro="LIQUIDO_PERITONEAL",
    ),
    MaterialPedidoDef(
        codigo="EFL_DIAL_PER",
        nombre="Efluente de diálisis peritoneal",
        sufijo="EDP",
        analitos=("ASP", "COL", "RAN"),
        celular=_cel("nc", "dif"),
        cultivo_micro="EFLUENTE_DIALISIS_PER",
        muestra_micro="EFLUENTE_DIALISIS_PER",
    ),
    MaterialPedidoDef(
        codigo="LIQ_PERICARD",
        nombre="Líquido pericárdico",
        sufijo="PRC",
        analitos=("ASP", "COL", "HTO", "PROT", "LDH", "GLU", "ADA"),
        celular=_cel("rbc", "nc", "dif", "citol"),
        cultivo_micro="LIQUIDO_PERICARDICO",
        muestra_micro="LIQUIDO_PERICARDICO",
    ),
    MaterialPedidoDef(
        codigo="LIQ_SINOVIAL",
        nombre="Líquido sinovial",
        sufijo="SIN",
        analitos=("ASP", "COL", "VISC", "CRIS", "GLU"),
        celular=_cel("rbc", "nc", "dif"),
        cultivo_micro="LIQUIDO_SINOVIAL",
        muestra_micro="LIQUIDO_SINOVIAL",
    ),
    MaterialPedidoDef(
        codigo="LIQ_ART_PP",
        nombre="Líquido articular periprotésico",
        sufijo="APP",
        analitos=("CRIS",),
        celular=_cel("rbc", "nc", "dif"),
        cultivo_micro="LIQ_ART_PERIPROTESICO",
        muestra_micro="LIQ_ART_PERIPROTESICO",
    ),
    MaterialPedidoDef(
        codigo="LIQ_Q_PANC",
        nombre="Líquido de quiste pancreático",
        sufijo="QPA",
        analitos=("AMIL", "CEA"),
        celular=_cel("citol"),
        cultivo_micro="LIQ_QUISTE_PANCREATICO",
        muestra_micro="LIQ_QUISTE_PANCREATICO",
    ),
    MaterialPedidoDef(
        codigo="LIQ_PQ_PANC",
        nombre="Líquido de pseudoquiste pancreático",
        sufijo="PQP",
        analitos=("AMIL",),
        celular=_cel("citol"),
        cultivo_micro="LIQ_PSEUDOQUISTE_PANC",
        muestra_micro="LIQ_PSEUDOQUISTE_PANC",
    ),
    MaterialPedidoDef(
        codigo="LIQ_DRENAJE",
        nombre="Líquido de drenaje posoperatorio",
        sufijo="DRN",
        analitos=("CREA", "BILI", "AMIL", "TG", "QUIL", "HTO"),
        cultivo_micro="LIQ_DRENAJE",
        muestra_micro="LIQ_DRENAJE",
    ),
    MaterialPedidoDef(
        codigo="ESPUTO",
        nombre="Esputo",
        sufijo="ESP",
        celular=_cel("citol"),
        cultivo_micro="ESPUTO",
        muestra_micro="ESPUTO",
        frecuente=True,
    ),
    MaterialPedidoDef(
        codigo="ASP_TRAQ",
        nombre="Aspirado traqueal",
        sufijo="ATR",
        cultivo_micro="ASPIRADO_TRAQUEAL_BRONQUIAL",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="ASP_ET",
        nombre="Aspirado endotraqueal",
        sufijo="AET",
        cultivo_micro="ASPIRADO_ENDOTRAQUEAL",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="BAL",
        nombre="Lavado broncoalveolar",
        sufijo="BAL",
        analitos=("HEMOS",),
        celular=_cel("nc", "dif", "citol"),
        cultivo_micro="MINI_BAL",
        muestra_micro="BAL",
    ),
    MaterialPedidoDef(
        codigo="LAV_BRONQ",
        nombre="Lavado bronquial",
        sufijo="LBR",
        celular=_cel("citol"),
        cultivo_micro="LAVADO_BRONQUIAL",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="CEP_BRONQ",
        nombre="Cepillado bronquial",
        sufijo="CBR",
        celular=_cel("citol"),
        cultivo_micro="CEPILLADO_BRONQUIAL",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="HISOP_FAR",
        nombre="Hisopado faríngeo",
        sufijo="HFA",
        cultivo_micro="NASOFARINGEO",
        muestra_micro="EXUDADO_FARINGEO",
    ),
    MaterialPedidoDef(
        codigo="HISOP_NAS",
        nombre="Hisopado nasal",
        sufijo="HNA",
        cultivo_micro="NASOFARINGEO",
        muestra_micro="EXUDADO_NASAL",
        frecuente=True,
    ),
    MaterialPedidoDef(
        codigo="HISOP_AMB",
        nombre="Hisopado ambiental",
        sufijo="HAM",
        cultivo_micro="AMBIENTAL",
        muestra_micro="HISOPADO_VIGILANCIA",
        frecuente=True,
    ),
    MaterialPedidoDef(
        codigo="ASP_SENO",
        nombre="Aspirado de seno paranasal",
        sufijo="ASN",
        cultivo_micro="ASPIRADO_SENO_PARANASAL",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="SEC_OTICA",
        nombre="Secreción ótica",
        sufijo="SOT",
        cultivo_micro="SEC_OTICA",
        muestra_micro="EXUDADO_OTICO",
    ),
    MaterialPedidoDef(
        codigo="LIQ_OIDO",
        nombre="Líquido de oído medio",
        sufijo="OMD",
        cultivo_micro="LIQ_OIDO_MEDIO",
        muestra_micro="EXUDADO_OTICO",
    ),
    MaterialPedidoDef(
        codigo="SEC_NASAL",
        nombre="Secreción nasal",
        sufijo="SNA",
        analitos=("B2TR", "BTRA"),
        cultivo_micro="SEC_NASAL",
        muestra_micro="EXUDADO_NASAL",
    ),
    MaterialPedidoDef(
        codigo="SEC_URETRAL",
        nombre="Secreción uretral",
        sufijo="SUR",
        cultivo_micro="URETRAL",
        muestra_micro="EXUDADO_GENITAL",
    ),
    MaterialPedidoDef(
        codigo="SEC_VAGINAL",
        nombre="Secreción vaginal",
        sufijo="SVA",
        cultivo_micro="VAGINAL",
        muestra_micro="EXUDADO_GENITAL",
    ),
    MaterialPedidoDef(
        codigo="SEC_ENDOCERV",
        nombre="Secreción endocervical",
        sufijo="ENC",
        cultivo_micro="VAGINAL",
        muestra_micro="EXUDADO_GENITAL",
    ),
    MaterialPedidoDef(
        codigo="HISOP_VAGR",
        nombre="Hisopado vaginorrectal",
        sufijo="HVR",
        cultivo_micro="SGB",
        muestra_micro="EXUDADO_GENITAL",
    ),
    MaterialPedidoDef(
        codigo="SEMEN",
        nombre="Semen",
        sufijo="SEM",
        analitos=("ESPM", "LEU", "FRUC"),
        cultivo_micro="CULTIVO_SEMEN",
        muestra_micro="SEMEN",
    ),
    MaterialPedidoDef(
        codigo="SEC_PROST",
        nombre="Secreción prostática",
        sufijo="SPR",
        analitos=("LEU",),
        cultivo_micro="SEC_PROSTATICA",
        muestra_micro="EXUDADO_GENITAL",
    ),
    MaterialPedidoDef(
        codigo="ABS_BART",
        nombre="Material de absceso de Bartolino",
        sufijo="BAR",
        cultivo_micro="ABS_BARTOLINO",
        muestra_micro="PUS",
    ),
    MaterialPedidoDef(
        codigo="MATERIA_FECAL",
        nombre="Materia fecal",
        sufijo="FEC",
        analitos=("SOH", "CALP", "ELAS", "GRAS"),
        cultivo_micro="COPROCULTIVO",
        muestra_micro="MATERIA_FECAL",
        color_tubo="Frasco",
        frecuente=True,
    ),
    MaterialPedidoDef(
        codigo="HISOP_RECT",
        nombre="Hisopado rectal",
        sufijo="HRE",
        cultivo_micro="HISOPADO_ANAL",
        muestra_micro="HISOPADO_VIGILANCIA",
        frecuente=True,
    ),
    MaterialPedidoDef(
        codigo="ASP_GASTR",
        nombre="Aspirado gástrico",
        sufijo="AGA",
        cultivo_micro="ASP_GASTRICO_BK",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="BIOP_GASTR",
        nombre="Biopsia gástrica",
        sufijo="BGA",
        analitos=("UREA",),
        cultivo_micro="BIOP_GASTR_HP",
        muestra_micro="BIOPSIA",
    ),
    MaterialPedidoDef(
        codigo="BILIS",
        nombre="Bilis",
        sufijo="BIL",
        cultivo_micro="CULTIVO_BILIS",
        muestra_micro="LIQUIDO_ESTERIL",
    ),
    MaterialPedidoDef(
        codigo="ABS_HEP",
        nombre="Material de absceso hepático",
        sufijo="AHE",
        cultivo_micro="ABS_HEPATICO",
        muestra_micro="PUS",
    ),
    MaterialPedidoDef(
        codigo="ABS_INTRAAB",
        nombre="Material de absceso intraabdominal",
        sufijo="AIA",
        cultivo_micro="ABS_INTRAABDOMINAL",
        muestra_micro="PUS",
    ),
    MaterialPedidoDef(
        codigo="PUS",
        nombre="Pus",
        sufijo="PUS",
        cultivo_micro="HERIDA_ABSCESO",
        muestra_micro="PUS",
    ),
    MaterialPedidoDef(
        codigo="EXUD_HERIDA",
        nombre="Exudado de herida",
        sufijo="EXH",
        cultivo_micro="HERIDA_ABSCESO",
        muestra_micro="PUS",
    ),
    MaterialPedidoDef(
        codigo="TEJ_PROF",
        nombre="Tejido profundo",
        sufijo="TPR",
        cultivo_micro="TEJIDO",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_CUT",
        nombre="Tejido cutáneo",
        sufijo="TCU",
        cultivo_micro="PIEL_PARTES_BLANDAS",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_SUBCUT",
        nombre="Tejido subcutáneo",
        sufijo="TSC",
        cultivo_micro="PIEL_PARTES_BLANDAS",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_MUSC",
        nombre="Tejido muscular",
        sufijo="TMU",
        cultivo_micro="TEJIDO",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_OSEO",
        nombre="Tejido óseo",
        sufijo="TOS",
        cultivo_micro="OSEO",
        muestra_micro="HUESO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_PP",
        nombre="Tejido periprotésico",
        sufijo="TPP",
        cultivo_micro="TEJ_PERIPROTESICO",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_PULM",
        nombre="Tejido pulmonar",
        sufijo="TPU",
        cultivo_micro="TEJIDO",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="TEJ_PLEU",
        nombre="Tejido pleural",
        sufijo="TPL",
        cultivo_micro="TEJIDO",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="MAT_GANGL",
        nombre="Material ganglionar",
        sufijo="GAN",
        analitos=("CITO",),
        celular=_cel("citol"),
        cultivo_micro="MAT_GANGLIONAR",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="ESC_PIEL",
        nombre="Escamas de piel",
        sufijo="EPI",
        cultivo_micro="HONGOS_ESCAMAS",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="PELOS",
        nombre="Pelos",
        sufijo="PEL",
        cultivo_micro="HONGOS_PELOS",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="UNAS",
        nombre="Uñas",
        sufijo="UNA",
        cultivo_micro="HONGOS_UNAS",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="PUNTA_CAT",
        nombre="Punta de catéter vascular",
        sufijo="CAT",
        cultivo_micro="PUNTA_CATETER",
        muestra_micro="CATETER",
    ),
    MaterialPedidoDef(
        codigo="LIQ_SONIC",
        nombre="Líquido de sonicación de prótesis",
        sufijo="SON",
        cultivo_micro="LIQ_SONICACION",
        muestra_micro="LIQUIDO_ESTERIL",
    ),
    MaterialPedidoDef(
        codigo="VALV_CARD",
        nombre="Válvula cardíaca",
        sufijo="VAL",
        cultivo_micro="VALVULA_CARDIACA",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="ASP_MEDULA",
        nombre="Aspirado de médula ósea",
        sufijo="AMO",
        analitos=("MIEL", "FE", "CITO", "CIGEN"),
        cultivo_micro="ASP_MEDULA_OSEA",
        muestra_micro="ASPIRADO",
    ),
    MaterialPedidoDef(
        codigo="LIQ_AMNIOT",
        nombre="Líquido amniótico",
        sufijo="AMN",
        analitos=("KARI", "CMA"),
        cultivo_micro="LIQ_AMNIOTICO",
        muestra_micro="LIQUIDO_ESTERIL",
    ),
    MaterialPedidoDef(
        codigo="PLACENTA",
        nombre="Placenta",
        sufijo="PLA",
        cultivo_micro="CULTIVO_PLACENTA",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="MEMB_OVUL",
        nombre="Membranas ovulares",
        sufijo="MOV",
        cultivo_micro="MEMBRANAS_OVULARES",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="PROD_CONCEP",
        nombre="Productos de concepción",
        sufijo="PCO",
        analitos=("KARI", "CMA"),
        cultivo_micro="PRODUCTOS_CONCEPCION",
        muestra_micro="TEJIDO",
    ),
    MaterialPedidoDef(
        codigo="HUMOR_ACU",
        nombre="Humor acuoso",
        sufijo="HAC",
        celular=_cel("citol"),
        cultivo_micro="HUMOR_ACUOSO",
        muestra_micro="LIQUIDO_ESTERIL",
    ),
    MaterialPedidoDef(
        codigo="HUMOR_VIT",
        nombre="Humor vítreo",
        sufijo="HVI",
        celular=_cel("citol"),
        cultivo_micro="HUMOR_VITREO",
        muestra_micro="LIQUIDO_ESTERIL",
    ),
    MaterialPedidoDef(
        codigo="RASP_CORN",
        nombre="Raspado corneal",
        sufijo="RCO",
        cultivo_micro="RASPADO_CORNEAL",
        muestra_micro="EXUDADO_OCULAR",
    ),
    MaterialPedidoDef(
        codigo="SEC_CONJ",
        nombre="Secreción conjuntival",
        sufijo="SCO",
        cultivo_micro="SEC_CONJUNTIVAL",
        muestra_micro="EXUDADO_OCULAR",
    ),
    MaterialPedidoDef(
        codigo="SUDOR",
        nombre="Sudor",
        sufijo="SUD",
        analitos=("CL",),
        cultivo_micro=None,
        muestra_micro=None,
    ),
    MaterialPedidoDef(
        codigo="CALC_URIN",
        nombre="Cálculo urinario",
        sufijo="CUR",
        analitos=("CALC",),
        cultivo_micro="CALCULO_URINARIO",
        muestra_micro="ORINA",
    ),
)


# Cultivos / muestras micro adicionales (aditivos; se suman al seed micro).
CULTIVOS_MICRO_EXTRA: tuple[tuple[str, str, int], ...] = (
    ("LIQUIDO_ASCITICO", "Cultivo de líquido ascítico", 205),
    ("EFLUENTE_DIALISIS_PER", "Cultivo de efluente de diálisis peritoneal", 206),
    ("LIQ_ART_PERIPROTESICO", "Cultivo de líquido articular periprotésico", 225),
    ("LIQ_QUISTE_PANCREATICO", "Cultivo de líquido de quiste pancreático", 232),
    ("LIQ_PSEUDOQUISTE_PANC", "Cultivo de líquido de pseudoquiste pancreático", 233),
    ("LIQ_DRENAJE", "Cultivo de líquido de drenaje", 234),
    ("ASPIRADO_ENDOTRAQUEAL", "Cultivo de aspirado endotraqueal", 95),
    ("LAVADO_BRONQUIAL", "Cultivo de lavado bronquial", 105),
    ("CEPILLADO_BRONQUIAL", "Cultivo de cepillado bronquial", 106),
    ("ASPIRADO_SENO_PARANASAL", "Cultivo de aspirado de seno paranasal", 75),
    ("SEC_OTICA", "Cultivo de secreción ótica", 107),
    ("LIQ_OIDO_MEDIO", "Cultivo de líquido de oído medio", 108),
    ("SEC_NASAL", "Cultivo de secreción nasal", 109),
    ("CULTIVO_SEMEN", "Cultivo de semen", 125),
    ("SEC_PROSTATICA", "Cultivo de secreción prostática", 126),
    ("ABS_BARTOLINO", "Cultivo de material de absceso de Bartolino", 127),
    ("ASP_GASTRICO_BK", "Cultivo de aspirado gástrico para micobacterias", 246),
    ("BIOP_GASTR_HP", "Cultivo de biopsia gástrica para Helicobacter pylori", 175),
    ("CULTIVO_BILIS", "Cultivo de bilis", 201),
    ("ABS_HEPATICO", "Cultivo de material de absceso hepático", 202),
    ("ABS_INTRAABDOMINAL", "Cultivo de material de absceso intraabdominal", 203),
    ("TEJ_PERIPROTESICO", "Cultivo de tejido periprotésico", 185),
    ("MAT_GANGLIONAR", "Cultivo de material ganglionar", 186),
    ("HONGOS_ESCAMAS", "Cultivo de escamas de piel para hongos", 251),
    ("HONGOS_PELOS", "Cultivo de pelos para hongos", 252),
    ("HONGOS_UNAS", "Cultivo de uñas para hongos", 253),
    ("LIQ_SONICACION", "Cultivo de líquido de sonicación de prótesis", 235),
    ("VALVULA_CARDIACA", "Cultivo de válvula cardíaca", 236),
    ("ASP_MEDULA_OSEA", "Cultivo de aspirado de médula ósea", 237),
    ("LIQ_AMNIOTICO", "Cultivo de líquido amniótico", 238),
    ("CULTIVO_PLACENTA", "Cultivo de placenta", 239),
    ("MEMBRANAS_OVULARES", "Cultivo de membranas ovulares", 240),
    ("PRODUCTOS_CONCEPCION", "Cultivo de productos de concepción", 241),
    ("HUMOR_ACUOSO", "Cultivo de humor acuoso", 242),
    ("HUMOR_VITREO", "Cultivo de humor vítreo", 243),
    ("RASPADO_CORNEAL", "Cultivo de raspado corneal", 244),
    ("SEC_CONJUNTIVAL", "Cultivo de secreción conjuntival", 245),
    ("CALCULO_URINARIO", "Cultivo de cálculo urinario", 41),
)

MUESTRAS_MICRO_EXTRA: tuple[tuple[str, str, int], ...] = (
    ("LIQUIDO_PLEURAL", "Líquido pleural", 131),
    ("LIQUIDO_ASCITICO", "Líquido ascítico", 132),
    ("LIQUIDO_PERITONEAL", "Líquido peritoneal", 133),
    ("LIQUIDO_PERICARDICO", "Líquido pericárdico", 134),
    ("LIQUIDO_SINOVIAL", "Líquido sinovial", 135),
    ("EFLUENTE_DIALISIS_PER", "Efluente diálisis peritoneal", 136),
    ("LIQ_ART_PERIPROTESICO", "Líquido articular periprotésico", 137),
    ("LIQ_QUISTE_PANCREATICO", "Líquido quiste pancreático", 138),
    ("LIQ_PSEUDOQUISTE_PANC", "Líquido pseudoquiste pancreático", 139),
    ("LIQ_DRENAJE", "Líquido de drenaje", 140),
    ("SEMEN", "Semen", 121),
)


# ---------------------------------------------------------------------------
# Expansión a exámenes / paneles / muestras
# ---------------------------------------------------------------------------


@dataclass
class ExamenMaterialDef:
    codigo: str
    nombre: str
    muestra: str
    tipo_resultado: str
    unidad_default: str = ""
    abreviatura: str = ""


@dataclass
class PanelMaterialDef:
    codigo: str
    nombre: str
    componentes: list[str] = field(default_factory=list)


def _analitos_por_bloque(
    mat: MaterialPedidoDef,
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    """Parte analitos: físicos / estudios / celulares / micro / químicos."""
    set_fis = set(ANALITOS_FISICOS)
    set_est = set(ANALITOS_ESTUDIOS)
    set_cel = set(ANALITOS_CELULARES)
    set_mic = set(ANALITOS_MICROS)
    fisicos = [k for k in ANALITOS_FISICOS if k in mat.analitos]
    estudios = [k for k in mat.analitos if k in set_est]
    celulares = [k for k in ANALITOS_CELULARES if k in mat.analitos]
    micros = [k for k in ANALITOS_MICROS if k in mat.analitos]
    quimicos = [
        k
        for k in mat.analitos
        if k not in set_fis
        and k not in set_est
        and k not in set_cel
        and k not in set_mic
    ]
    return fisicos, estudios, celulares, micros, quimicos


def _examen_de_analito(mat: MaterialPedidoDef, key: str) -> ExamenMaterialDef:
    meta = ANALITOS[key]
    return ExamenMaterialDef(
        codigo=_code(key, mat.sufijo),
        nombre=f"{meta['nombre']} ({mat.nombre})",
        muestra=mat.codigo,
        tipo_resultado=meta["tipo_resultado"],
        unidad_default=meta.get("unidad") or "",
        abreviatura=key[:12],
    )


def examenes_de_material(mat: MaterialPedidoDef) -> list[ExamenMaterialDef]:
    """TipoExamen a sembrar para un material (sin paneles).

    Orden: físicos → estudios → recuentos/diferencial → microscopia → químicos.
    """
    if mat.ui_preset in ("sangre", "orina"):
        return []
    out: list[ExamenMaterialDef] = []
    fisicos, estudios, celulares_analitos, micros, quimicos = _analitos_por_bloque(mat)

    for key in fisicos:
        out.append(_examen_de_analito(mat, key))
    for key in estudios:
        out.append(_examen_de_analito(mat, key))

    if "rbc" in mat.celular:
        out.append(_examen_de_analito(mat, "RBC"))
    if "nc" in mat.celular:
        out.append(_examen_de_analito(mat, "NC"))
    for key in celulares_analitos:
        # RBC/NC ya salieron del bloque celular si también están en flags.
        if key == "RBC" and "rbc" in mat.celular:
            continue
        if key == "NC" and "nc" in mat.celular:
            continue
        out.append(_examen_de_analito(mat, key))
    if "dif" in mat.celular:
        for pref, nom in DIFERENCIAL_COMPONENTES:
            out.append(
                ExamenMaterialDef(
                    codigo=_code(pref, mat.sufijo),
                    nombre=f"{nom} % ({mat.nombre})",
                    muestra=mat.codigo,
                    tipo_resultado="NUMERICO",
                    unidad_default="%",
                    abreviatura=pref,
                )
            )
    for key in micros:
        out.append(_examen_de_analito(mat, key))
    if "citol" in mat.celular and "CITOL" not in mat.analitos:
        out.append(_examen_de_analito(mat, "CITOL"))

    for key in quimicos:
        out.append(_examen_de_analito(mat, key))
    return out


def panel_diferencial_de_material(mat: MaterialPedidoDef) -> PanelMaterialDef | None:
    if "dif" not in mat.celular:
        return None
    suf = mat.sufijo
    return PanelMaterialDef(
        codigo=_code("PAN_DIF", suf),
        nombre=f"Diferencial celular ({mat.nombre})",
        componentes=[_code(pref, suf) for pref, _ in DIFERENCIAL_COMPONENTES],
    )


def grilla_codigos_material(mat: MaterialPedidoDef) -> list[str]:
    """Códigos pedibles en un clic (exámenes + panel diferencial).

    Orden: físicos → estudios → recuentos/diferencial → microscopia → químicos.
    """
    if mat.ui_preset in ("sangre", "orina"):
        return []
    fisicos, estudios, celulares_analitos, micros, quimicos = _analitos_por_bloque(mat)
    codes: list[str] = [_code(k, mat.sufijo) for k in fisicos]
    codes.extend(_code(k, mat.sufijo) for k in estudios)
    if "rbc" in mat.celular:
        codes.append(_code("RBC", mat.sufijo))
    if "nc" in mat.celular:
        codes.append(_code("NC", mat.sufijo))
    for key in celulares_analitos:
        if key == "RBC" and "rbc" in mat.celular:
            continue
        if key == "NC" and "nc" in mat.celular:
            continue
        codes.append(_code(key, mat.sufijo))
    pan = panel_diferencial_de_material(mat)
    if pan:
        codes.append(pan.codigo)
    for key in micros:
        codes.append(_code(key, mat.sufijo))
    if "citol" in mat.celular and "CITOL" not in mat.analitos:
        codes.append(_code("CITOL", mat.sufijo))
    codes.extend(_code(k, mat.sufijo) for k in quimicos)
    return codes


def prefijo_codigo_material(codigo: str) -> str | None:
    """Prefijo de analito/panel material (ASP, PAN_DIF, NEUT, …) o None."""
    c = (codigo or "").strip().upper()
    if not c:
        return None
    for pref in _PREFIJOS_MATCH_ORDEN:
        if c == pref or c.startswith(f"{pref}_"):
            return pref
    return None


def rank_presentacion_codigo_material(codigo: str) -> int | None:
    """Rank físicos→celulares→químicos para códigos del catálogo materiales.

    None si el código no pertenece a materiales de pedido (sangre/orina legacy
    siguen ORDEN_PRESENTACION_PEDIDO).
    """
    c = (codigo or "").strip().upper()
    if not c or c not in _CODIGOS_MATERIAL_PEDIDO:
        return None
    pref = prefijo_codigo_material(c)
    if pref is None:
        return 9_000
    return _PREFIJO_ORDEN_RANK.get(pref, 9_000)


def todas_muestras_clinicas() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for mat in MATERIALES_PEDIDO:
        if mat.ui_preset in ("sangre", "orina"):
            continue
        out[mat.codigo] = {
            "nombre": mat.nombre,
            "color_tubo": mat.color_tubo,
        }
    return out


def todos_examenes_materiales() -> list[ExamenMaterialDef]:
    by_code: dict[str, ExamenMaterialDef] = {}
    for mat in MATERIALES_PEDIDO:
        for ex in examenes_de_material(mat):
            by_code[ex.codigo] = ex
    return list(by_code.values())


def todos_paneles_materiales() -> list[PanelMaterialDef]:
    out: list[PanelMaterialDef] = []
    for mat in MATERIALES_PEDIDO:
        pan = panel_diferencial_de_material(mat)
        if pan:
            out.append(pan)
    return out


def material_por_codigo(codigo: str) -> MaterialPedidoDef | None:
    c = (codigo or "").strip().upper()
    for mat in MATERIALES_PEDIDO:
        if mat.codigo == c:
            return mat
    return None


def as_api_list() -> list[dict[str, Any]]:
    """Serialización estable para GET materiales-pedido."""
    from laboratorio.muestra_sangre_pedido import codigos_tipo_muestra_sangre_en_db

    rows: list[dict[str, Any]] = []
    sangre_codigos: list[str] | None = None
    for mat in MATERIALES_PEDIDO:
        tipo_muestras = list(mat.tipo_muestra_codigos_extra) or [mat.codigo]
        # Sangre: todas las variantes de sangre/suero/plasma en catálogo (no solo canónicos).
        if mat.codigo == "SANGRE" or mat.ui_preset == "sangre":
            if sangre_codigos is None:
                from django.apps import apps

                if apps.ready:
                    try:
                        sangre_codigos = codigos_tipo_muestra_sangre_en_db(
                            solo_activos=True
                        )
                    except RuntimeError:
                        # Tests sin mark django_db / sin conexión: lista canónica.
                        sangre_codigos = list(tipo_muestras)
                else:
                    sangre_codigos = list(tipo_muestras)
            tipo_muestras = sorted({*tipo_muestras, *(sangre_codigos or [])})
        rows.append(
            {
                "codigo": mat.codigo,
                "nombre": mat.nombre,
                "ui_preset": mat.ui_preset or None,
                "tipo_muestra_codigos": tipo_muestras,
                "grilla_codigos": grilla_codigos_material(mat),
                "cultivo_micro_codigo": mat.cultivo_micro,
                "muestra_micro_codigo": mat.muestra_micro,
                "tiene_estudio_celular": bool(mat.celular),
                "frecuente": bool(mat.frecuente),
            }
        )
    return rows


def codigos_examen_materiales() -> frozenset[str]:
    return frozenset(e.codigo for e in todos_examenes_materiales())


_CODIGOS_MATERIAL_PEDIDO: frozenset[str] = frozenset(
    e.codigo for e in todos_examenes_materiales()
) | frozenset(p.codigo for p in todos_paneles_materiales())


# Validación al importar
for _mat in MATERIALES_PEDIDO:
    for _ex in examenes_de_material(_mat):
        assert len(_ex.codigo) <= 20, _ex.codigo
    _pan = panel_diferencial_de_material(_mat)
    if _pan:
        assert len(_pan.codigo) <= 20, _pan.codigo
