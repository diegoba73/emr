"""
Branding y textos del informe PDF LIMS (formato ICPL Pueblo de Luis).

Ajustá estos valores sin tocar la lógica de layout.
"""
from __future__ import annotations

from pathlib import Path

LABORATORIO_STATIC = Path(__file__).resolve().parent / "static" / "laboratorio"

INFORME_LAB_CONFIG = {
    "titulo": "Laboratorio de Análisis Clínicos Pueblo de Luis",
    "subtitulo_informe": "Informe de resultados",
    "institucion_corta": "Instituto de Cardiología Pueblo de Luis",
    "direccion_linea": "Inmigrantes 50 | Trelew | Chubut",
    "contacto_linea": (
        "Tel: (0280) 4429966 | laboratorio@icpueblodeluis.com.ar | www.icpueblodeluis.com.ar"
    ),
    "firmas": [
        {
            "nombre": "Bioq. Sebastián Fuentealba",
            "mp": "0507",
            "imagen": "firma_1.png",
        },
        {
            "nombre": "Bioq. Diego A. Bayide",
            "mp": "0489",
            "imagen": "firma_2.png",
        },
    ],
    "logo": "icpl_logo.png",
    # Métodos analíticos por código de examen (fallback si el modelo no tiene metodo).
    "metodos_por_codigo": {
        "GLU": "Enzimático colorimétrico",
        "HEMO": "Contador hematológico",
        "COL": "Enzimático colorimétrico",
        "URE": "Colorimétrico",
        "CREA": "Jaffé cinético",
    },
    "metodo_default": "",
}

# Tipografía — título examen 9pt → método/ref 6pt (≈2/3)
INFORME_TYPO = {
    "panel_title": 10,
    "panel_meta": 7,
    "exam_title": 9,
    "exam_meta": 6,
    "result_value": 9,
    "result_unit": 8,
    "header_label": 7.5,
    "header_value": 8,
    "table_header": 7,
    "color_meta": "#4A4A4A",
    "color_rule": "#333333",
    "color_panel_bg": "#F4F4F4",
}

MESES_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
