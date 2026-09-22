"""Catálogo confirmado de reactivos por equipo (Ticket B).

Solo datos de producto InsumoLab + equipo + REF.
NO incluye ConsumoInsumoExamen (descuenta stock al cargar).
Correspondencias LIS se documentan en `lis_codigos` para la matriz, sin persistir consumo.
"""
from __future__ import annotations

from typing import TypedDict


class ReactivoCatalogoRow(TypedDict):
    codigo: str  # SKU interno estable
    nombre: str
    ref_comercial: str
    equipo_codigo: str
    proveedor: str
    unidad: str
    lis_codigos: list[str]  # documentación; no crea ConsumoInsumoExamen
    estado: str  # CONFIRMADO | PENDIENTE


# Productos Wiener / VIDAS / Finecare confirmados por el lab.
# No incluye FERR (REF pendiente). No toca CRE/GLU Pharmacorp (códigos distintos).
REACTIVOS_CATALOGO_CONFIRMADOS: list[ReactivoCatalogoRow] = [
    {
        "codigo": "R-1008109",
        "nombre": "Wiener Uricostat",
        "ref_comercial": "1008109",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["AU"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008156",
        "nombre": "Wiener Albumin",
        "ref_comercial": "1008156",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["ALB"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008157",
        "nombre": "Wiener Colesterol total",
        "ref_comercial": "1008157",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["COL_TOT"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008149",
        "nombre": "Wiener Creatinina enzimática",
        "ref_comercial": "1008149",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["CREATI"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008158",
        "nombre": "Wiener Glicemia enzimática GOD/POD",
        "ref_comercial": "1008158",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["GLU"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1009804",
        "nombre": "Wiener HDL Cholesterol fast",
        "ref_comercial": "1009804",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["HDL"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008159",
        "nombre": "Wiener Proteínas totales",
        "ref_comercial": "1008159",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["PROT_T"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008160",
        "nombre": "Wiener Triglicéridos",
        "ref_comercial": "1008160",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["TG"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008108",
        "nombre": "Wiener Urea",
        "ref_comercial": "1008108",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["UREA"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008111",
        "nombre": "Wiener AST/GOT",
        "ref_comercial": "1008111",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["GOT"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008112",
        "nombre": "Wiener ALT/GPT",
        "ref_comercial": "1008112",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["GPT"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008110",
        "nombre": "Wiener Fosfatasa alcalina",
        "ref_comercial": "1008110",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["FAL"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008121",
        "nombre": "Wiener LDH-L",
        "ref_comercial": "1008121",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["LDH"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008145",
        "nombre": "Wiener Mg-color AA",
        "ref_comercial": "1008145",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["MG"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008100",
        "nombre": "Wiener CRP hs Turbitest AA",
        "ref_comercial": "1008100",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["PCR_US"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008161",
        "nombre": "Wiener Proti U/LCR",
        "ref_comercial": "1008161",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["PROT_U_AZ", "PROT_U_24"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008125",
        "nombre": "Wiener PCR Turbitest AA",
        "ref_comercial": "1008125",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["PCR"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-1008123",
        "nombre": "Wiener UIBC/TIBC AA líquida",
        "ref_comercial": "1008123",
        "equipo_codigo": "CM260",
        "proveedor": "Wiener",
        "unidad": "cartucho",
        "lis_codigos": ["CF"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-415386",
        "nombre": "bioMérieux VIDAS TNHS",
        "ref_comercial": "415386",
        "equipo_codigo": "VIDAS_KUBE",
        "proveedor": "bioMérieux",
        "unidad": "test",
        "lis_codigos": ["TROP_US"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-30400",
        "nombre": "bioMérieux VIDAS TSH",
        "ref_comercial": "30400",
        "equipo_codigo": "VIDAS_KUBE",
        "proveedor": "bioMérieux",
        "unidad": "test",
        "lis_codigos": ["TSH"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-W227",
        "nombre": "Finecare One Step D-Dimer Rapid Quantitative Test",
        "ref_comercial": "W227",
        "equipo_codigo": "FINECARE",
        "proveedor": "Wondfo",
        "unidad": "test",
        "lis_codigos": ["DDIM"],
        "estado": "CONFIRMADO",
    },
    {
        "codigo": "R-W216",
        "nombre": "Finecare panel cTnI/Myoglobin/CK-MB",
        "ref_comercial": "W216",
        "equipo_codigo": "FINECARE",
        "proveedor": "Wondfo",
        "unidad": "test",
        "lis_codigos": ["CPK_MB", "MIOG", "TROP_I"],
        "estado": "CONFIRMADO",
    },
]

# Documentados como pendientes (no se cargan).
REACTIVOS_CATALOGO_PENDIENTES: list[dict[str, str]] = [
    {
        "equipo_codigo": "CM260",
        "nombre": "Wiener hierro / ferremia",
        "ref_comercial": "",
        "lis": "FERR",
        "motivo": "REF_PENDIENTE",
    },
]

# Códigos internos legacy que no deben sobrescribirse.
SKU_LEGACY_NO_TOCAR: frozenset[str] = frozenset({"CRE", "GLU"})
