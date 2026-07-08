"""
Valores de referencia, unidades y métodos analíticos del catálogo LIMS ICPL.

Clave: código de ``TipoExamen`` (``catalogo_solicitud_papel.EXAMENES``).
Rangos orientados a adultos; sin estratificación por edad/sexo (alcance B4.1).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict


class ReferenciaClinicaDef(TypedDict, total=False):
    metodo: str
    unidad_default: str
    rango_referencia_texto: str
    rango_min: Decimal
    rango_max: Decimal
    valor_critico_min: Decimal
    valor_critico_max: Decimal


def _r(
    *,
    metodo: str,
    unidad: str = "",
    ref: str = "",
    rmin: str | None = None,
    rmax: str | None = None,
    cmin: str | None = None,
    cmax: str | None = None,
) -> ReferenciaClinicaDef:
    out: ReferenciaClinicaDef = {"metodo": metodo}
    if unidad:
        out["unidad_default"] = unidad
    if ref:
        out["rango_referencia_texto"] = ref
    if rmin is not None:
        out["rango_min"] = Decimal(rmin)
    if rmax is not None:
        out["rango_max"] = Decimal(rmax)
    if cmin is not None:
        out["valor_critico_min"] = Decimal(cmin)
    if cmax is not None:
        out["valor_critico_max"] = Decimal(cmax)
    return out


# Métodos reutilizados
_M_HEMO = "Contador hematológico automatizado"
_M_ENZ = "Enzimático colorimétrico"
_M_ENZ_UV = "Enzimático cinético UV"
_M_ISE = "Electrodo selectivo de iones (ISE)"
_M_COAG = "Coagulometría óptica"
_M_INMUNO = "Inmunoturbidimetría"
_M_QUIM = "Quimioluminiscencia"
_M_ELP = "Electroforesis en gel de agarosa"
_M_ORI_TIRA = "Tira reactiva"
_M_ORI_MICRO = "Microscopía"
_M_ORI_REFR = "Refractometría"
_M_EAB = "Electrodo selectivo de iones (gasometría)"

REFERENCIAS_POR_CODIGO: dict[str, ReferenciaClinicaDef] = {
    # —— Hemograma ——
    "HEMATIES": _r(
        metodo=_M_HEMO,
        unidad="mill/mm³",
        ref="4.0 - 5.5 mill/mm³",
        rmin="4.0",
        rmax="5.5",
    ),
    "HGB": _r(
        metodo=_M_HEMO,
        unidad="g/dL",
        ref="12 - 16 g/dL",
        rmin="12",
        rmax="16",
        cmin="7",
        cmax="20",
    ),
    "HTO": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="36 - 48 %",
        rmin="36",
        rmax="48",
    ),
    "RDW": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="11.5 - 14.5 %",
        rmin="11.5",
        rmax="14.5",
    ),
    "LEU": _r(
        metodo=_M_HEMO,
        unidad="/mm³",
        ref="4000 - 10000 /mm³",
        rmin="4000",
        rmax="10000",
    ),
    "NEUT_CAY": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="0 - 5 %",
        rmin="0",
        rmax="5",
    ),
    "NEUT_SEG": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="40 - 70 %",
        rmin="40",
        rmax="70",
    ),
    "EOS": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="1 - 4 %",
        rmin="1",
        rmax="4",
    ),
    "BAS": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="0 - 1 %",
        rmin="0",
        rmax="1",
    ),
    "LINF": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="20 - 45 %",
        rmin="20",
        rmax="45",
    ),
    "MONO": _r(
        metodo=_M_HEMO,
        unidad="%",
        ref="2 - 10 %",
        rmin="2",
        rmax="10",
    ),
    "PLAQ": _r(
        metodo=_M_HEMO,
        unidad="/mm³",
        ref="150000 - 450000 /mm³",
        rmin="150000",
        rmax="450000",
        cmin="50000",
        cmax="1000000",
    ),
    # —— Perfil lipídico ——
    "COL_TOT": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="< 200 mg/dL",
        rmax="200",
    ),
    "HDL": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="> 40 mg/dL",
        rmin="40",
    ),
    "LDL": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="< 130 mg/dL",
        rmax="130",
    ),
    "COL_NO_LDL": _r(
        metodo="Calculado (Friedewald)",
        unidad="mg/dL",
        ref="< 130 mg/dL",
        rmax="130",
    ),
    "TG": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="< 150 mg/dL",
        rmax="150",
    ),
    # —— Hepatograma ——
    "GOT": _r(
        metodo=_M_ENZ_UV,
        unidad="U/L",
        ref="5 - 40 U/L",
        rmin="5",
        rmax="40",
    ),
    "GPT": _r(
        metodo=_M_ENZ_UV,
        unidad="U/L",
        ref="5 - 41 U/L",
        rmin="5",
        rmax="41",
    ),
    "FAL": _r(
        metodo=_M_ENZ,
        unidad="U/L",
        ref="40 - 129 U/L",
        rmin="40",
        rmax="129",
    ),
    "BIL_T": _r(
        metodo="Colorimétrico diazo",
        unidad="mg/dL",
        ref="0.3 - 1.2 mg/dL",
        rmin="0.3",
        rmax="1.2",
    ),
    "BIL_D": _r(
        metodo="Colorimétrico diazo",
        unidad="mg/dL",
        ref="0.0 - 0.3 mg/dL",
        rmin="0.0",
        rmax="0.3",
    ),
    # —— Ionograma plasmático ——
    "NA": _r(
        metodo=_M_ISE,
        unidad="mEq/L",
        ref="136 - 145 mEq/L",
        rmin="136",
        rmax="145",
        cmin="120",
        cmax="160",
    ),
    "K": _r(
        metodo=_M_ISE,
        unidad="mEq/L",
        ref="3.5 - 5.1 mEq/L",
        rmin="3.5",
        rmax="5.1",
        cmin="2.5",
        cmax="6.5",
    ),
    "CL": _r(
        metodo=_M_ISE,
        unidad="mEq/L",
        ref="98 - 106 mEq/L",
        rmin="98",
        rmax="106",
    ),
    # —— Coagulograma ——
    "TP": _r(
        metodo=_M_COAG,
        unidad="seg",
        ref="11 - 14.5 seg",
        rmin="11",
        rmax="14.5",
    ),
    "PP": _r(
        metodo=_M_COAG,
        unidad="%",
        ref="70 - 100 %",
        rmin="70",
        rmax="100",
    ),
    "INR": _r(
        metodo=_M_COAG,
        unidad="",
        ref="0.8 - 1.2",
        rmin="0.8",
        rmax="1.2",
    ),
    "KPTT": _r(
        metodo=_M_COAG,
        unidad="seg",
        ref="25 - 35 seg",
        rmin="25",
        rmax="35",
    ),
    # —— Perfil férrico ——
    "CF": _r(
        metodo="Colorimétrico",
        unidad="µg/dL",
        ref="250 - 450 µg/dL",
        rmin="250",
        rmax="450",
    ),
    "FERR": _r(
        metodo="Colorimétrico",
        unidad="µg/dL",
        ref="60 - 170 µg/dL",
        rmin="60",
        rmax="170",
    ),
    "TRANS": _r(
        metodo=_M_INMUNO,
        unidad="mg/dL",
        ref="200 - 360 mg/dL",
        rmin="200",
        rmax="360",
    ),
    "FERRIT": _r(
        metodo=_M_INMUNO,
        unidad="ng/mL",
        ref="12 - 300 ng/mL",
        rmin="12",
        rmax="300",
    ),
    "SAT_FE": _r(
        metodo="Calculado",
        unidad="%",
        ref="20 - 50 %",
        rmin="20",
        rmax="50",
    ),
    # —— Orina completa ——
    "ORI_COLOR": _r(metodo="Inspección visual", ref="Amarillo claro"),
    "ORI_ASP": _r(metodo="Inspección visual", ref="Limpio"),
    "ORI_DENS": _r(
        metodo=_M_ORI_REFR,
        unidad="",
        ref="1.005 - 1.030",
        rmin="1.005",
        rmax="1.030",
    ),
    "ORI_PH": _r(
        metodo=_M_ORI_TIRA,
        unidad="",
        ref="5.0 - 8.0",
        rmin="5.0",
        rmax="8.0",
    ),
    "ORI_BIL": _r(metodo=_M_ORI_TIRA, ref="Negativo"),
    "ORI_NIT": _r(metodo=_M_ORI_TIRA, ref="Negativo"),
    "ORI_CET": _r(metodo=_M_ORI_TIRA, ref="Negativo"),
    "ORI_CEL": _r(metodo=_M_ORI_MICRO, ref="0 - 5/campo"),
    "ORI_LEU": _r(metodo=_M_ORI_TIRA, ref="Negativo"),
    "ORI_HEM": _r(metodo=_M_ORI_TIRA, ref="Negativo"),
    "ORI_PIO": _r(metodo=_M_ORI_MICRO, ref="Ausentes"),
    "ORI_MUC": _r(metodo=_M_ORI_MICRO, ref="Ausente / escaso"),
    "ORI_CRIS": _r(metodo=_M_ORI_MICRO, ref="Ausentes"),
    "ORI_CONC": _r(metodo="Integración clínica", ref="Según hallazgos"),
    # —— Ionograma urinario ——
    "NA_U": _r(
        metodo=_M_ISE,
        unidad="mEq/L",
        ref="40 - 220 mEq/L",
        rmin="40",
        rmax="220",
    ),
    "K_U": _r(
        metodo=_M_ISE,
        unidad="mEq/L",
        ref="25 - 125 mEq/L",
        rmin="25",
        rmax="125",
    ),
    "CL_U": _r(
        metodo=_M_ISE,
        unidad="mEq/L",
        ref="110 - 250 mEq/L",
        rmin="110",
        rmax="250",
    ),
    # —— Proteinograma ——
    "ELP_ALB": _r(
        metodo=_M_ELP,
        unidad="%",
        ref="55 - 65 %",
        rmin="55",
        rmax="65",
    ),
    "ELP_A1": _r(
        metodo=_M_ELP,
        unidad="%",
        ref="2 - 5 %",
        rmin="2",
        rmax="5",
    ),
    "ELP_A2": _r(
        metodo=_M_ELP,
        unidad="%",
        ref="7 - 13 %",
        rmin="7",
        rmax="13",
    ),
    "ELP_B1": _r(
        metodo=_M_ELP,
        unidad="%",
        ref="4 - 8 %",
        rmin="4",
        rmax="8",
    ),
    "ELP_B2": _r(
        metodo=_M_ELP,
        unidad="%",
        ref="3 - 7 %",
        rmin="3",
        rmax="7",
    ),
    "ELP_GAM": _r(
        metodo=_M_ELP,
        unidad="%",
        ref="11 - 22 %",
        rmin="11",
        rmax="22",
    ),
    "ELP_CONC": _r(metodo=_M_ELP, ref="Según patrón electroforético"),
    # —— Clearance / microalbuminuria ——
    "CREA_U": _r(
        metodo="Jaffé cinético",
        unidad="mg/dL",
        ref="Según clearance",
    ),
    "DIUR": _r(
        metodo="Medición volumétrica",
        unidad="mL/24 hs",
        ref="800 - 2000 mL/24 hs",
        rmin="800",
        rmax="2000",
    ),
    "CLEAR_CREA": _r(
        metodo="Calculado",
        unidad="mL/min",
        ref="90 - 120 mL/min",
        rmin="90",
        rmax="120",
    ),
    "MICROALB": _r(
        metodo=_M_INMUNO,
        unidad="mg/L",
        ref="< 30 mg/L",
        rmax="30",
    ),
    # —— Exámenes sueltos ——
    "HBA1C": _r(
        metodo="Cromatografía de intercambio iónico / HPLC",
        unidad="%",
        ref="4.0 - 6.0 %",
        rmin="4.0",
        rmax="6.0",
    ),
    "GLU": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="70 - 100 mg/dL",
        rmin="70",
        rmax="100",
        cmin="40",
        cmax="400",
    ),
    "UREA": _r(
        metodo="Ureasa-GLDH",
        unidad="mg/dL",
        ref="15 - 45 mg/dL",
        rmin="15",
        rmax="45",
    ),
    "CREA": _r(
        metodo="Jaffé cinético",
        unidad="mg/dL",
        ref="0.6 - 1.2 mg/dL",
        rmin="0.6",
        rmax="1.2",
    ),
    "AU": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="3.5 - 7.0 mg/dL",
        rmin="3.5",
        rmax="7.0",
    ),
    "CA": _r(
        metodo="Colorimétrico (Arsenazo III)",
        unidad="mg/dL",
        ref="8.5 - 10.5 mg/dL",
        rmin="8.5",
        rmax="10.5",
        cmin="6",
        cmax="13",
    ),
    "MG": _r(
        metodo="Colorimétrico",
        unidad="mg/dL",
        ref="1.7 - 2.4 mg/dL",
        rmin="1.7",
        rmax="2.4",
    ),
    "P": _r(
        metodo="Colorimétrico (molibdato)",
        unidad="mg/dL",
        ref="2.5 - 4.5 mg/dL",
        rmin="2.5",
        rmax="4.5",
    ),
    "CA_ION": _r(
        metodo=_M_ISE,
        unidad="mmol/L",
        ref="1.12 - 1.32 mmol/L",
        rmin="1.12",
        rmax="1.32",
    ),
    "PROT_T": _r(
        metodo="Colorimétrico (Biuret)",
        unidad="g/dL",
        ref="6.0 - 8.0 g/dL",
        rmin="6.0",
        rmax="8.0",
    ),
    "ALB": _r(
        metodo="Colorimétrico (Verde de bromocresol)",
        unidad="g/dL",
        ref="3.5 - 5.0 g/dL",
        rmin="3.5",
        rmax="5.0",
    ),
    "VSG": _r(
        metodo="Westergren",
        unidad="mm/h",
        ref="0 - 20 mm/h",
        rmin="0",
        rmax="20",
    ),
    "PCR_US": _r(
        metodo=_M_INMUNO,
        unidad="mg/L",
        ref="< 3 mg/L",
        rmax="3",
    ),
    "AMIL": _r(
        metodo=_M_ENZ,
        unidad="U/L",
        ref="28 - 100 U/L",
        rmin="28",
        rmax="100",
    ),
    "LIP": _r(
        metodo=_M_ENZ,
        unidad="U/L",
        ref="13 - 60 U/L",
        rmin="13",
        rmax="60",
    ),
    "GGT": _r(
        metodo=_M_ENZ,
        unidad="U/L",
        ref="8 - 61 U/L",
        rmin="8",
        rmax="61",
    ),
    "LDH": _r(
        metodo=_M_ENZ,
        unidad="U/L",
        ref="125 - 220 U/L",
        rmin="125",
        rmax="220",
    ),
    "CPK": _r(
        metodo=_M_ENZ,
        unidad="U/L",
        ref="30 - 200 U/L",
        rmin="30",
        rmax="200",
    ),
    "CPK_MB": _r(
        metodo=_M_INMUNO,
        unidad="ng/mL",
        ref="< 5 ng/mL",
        rmax="5",
    ),
    "TROP_I": _r(
        metodo=_M_INMUNO,
        unidad="ng/mL",
        ref="< 0.04 ng/mL",
        rmax="0.04",
    ),
    "TROP_US": _r(
        metodo=_M_INMUNO,
        unidad="ng/L",
        ref="< 14 ng/L",
        rmax="14",
    ),
    "MIOG": _r(
        metodo=_M_INMUNO,
        unidad="ng/mL",
        ref="< 90 ng/mL",
        rmax="90",
    ),
    "PROBNP": _r(
        metodo=_M_INMUNO,
        unidad="pg/mL",
        ref="< 125 pg/mL",
        rmax="125",
    ),
    "DDIM": _r(
        metodo=_M_INMUNO,
        unidad="µg/mL",
        ref="< 0.5 µg/mL",
        rmax="0.5",
    ),
    "PROT_U_24": _r(
        metodo="Colorimétrico (Pirocatecol)",
        unidad="mg/24 hs",
        ref="< 150 mg/24 hs",
        rmax="150",
    ),
    "PROT_U_AZ": _r(
        metodo="Colorimétrico (Pirocatecol)",
        unidad="mg/dL",
        ref="< 20 mg/dL",
        rmax="20",
    ),
    "LPA": _r(
        metodo=_M_INMUNO,
        unidad="mg/dL",
        ref="< 30 mg/dL",
        rmax="30",
    ),
    "PSA": _r(
        metodo=_M_INMUNO,
        unidad="ng/mL",
        ref="< 4 ng/mL",
        rmax="4",
    ),
    "TSH": _r(
        metodo=_M_QUIM,
        unidad="µUI/mL",
        ref="0.4 - 4.0 µUI/mL",
        rmin="0.4",
        rmax="4.0",
    ),
    "T3": _r(
        metodo=_M_QUIM,
        unidad="ng/dL",
        ref="80 - 200 ng/dL",
        rmin="80",
        rmax="200",
    ),
    "T4": _r(
        metodo=_M_QUIM,
        unidad="µg/dL",
        ref="4.5 - 12.0 µg/dL",
        rmin="4.5",
        rmax="12.0",
    ),
    "T4L": _r(
        metodo=_M_QUIM,
        unidad="ng/dL",
        ref="0.8 - 1.8 ng/dL",
        rmin="0.8",
        rmax="1.8",
    ),
    "B12": _r(
        metodo=_M_QUIM,
        unidad="pg/mL",
        ref="200 - 900 pg/mL",
        rmin="200",
        rmax="900",
    ),
    "VITD": _r(
        metodo=_M_QUIM,
        unidad="ng/mL",
        ref="30 - 100 ng/mL",
        rmin="30",
        rmax="100",
    ),
    "EAB_ART": _r(metodo=_M_EAB, ref="Según valores de gasometría arterial"),
    "EAB_VEN": _r(metodo=_M_EAB, ref="Según valores de gasometría venosa"),
    "LACT": _r(
        metodo=_M_ENZ,
        unidad="mmol/L",
        ref="0.5 - 2.2 mmol/L",
        rmin="0.5",
        rmax="2.2",
        cmax="4",
    ),
}

# Códigos legacy del seed demo (referencias alineadas al catálogo nuevo)
REFERENCIAS_LEGACY: dict[str, ReferenciaClinicaDef] = {
    "HEMO": _r(metodo=_M_HEMO, ref="Ver componentes del hemograma"),
    "COL": _r(
        metodo=_M_ENZ,
        unidad="mg/dL",
        ref="< 200 mg/dL",
        rmax="200",
    ),
}
