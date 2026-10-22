"""
Curva / prueba oral de tolerancia a la glucosa (CTOG).

Panel ``PAN_CTOG``: glucemia basal (0 min) + 120 minutos.
No se informa el punto a 60 minutos.
"""
from __future__ import annotations

PANEL_CTOG = "PAN_CTOG"

CODIGO_GLU_BASAL = "GLU_0"
CODIGO_GLU_120 = "GLU120"

# Orden de filas en carga / informe.
CODIGOS_CTOG: tuple[str, ...] = (CODIGO_GLU_BASAL, CODIGO_GLU_120)

ETIQUETAS_CTOG: dict[str, str] = {
    CODIGO_GLU_BASAL: "Basal (0 min)",
    CODIGO_GLU_120: "120 minutos",
}

TITULO_INFORME_CTOG = "PRUEBA ORAL DE TOLERANCIA A LA GLUCOSA"
MUESTRA_INFORME_CTOG = "Plasma venoso"
METODO_INFORME_CTOG = "Enzimático"
SOBRECARGA_INFORME_CTOG = "75 g de glucosa anhidra"

REF_CTOG: dict[str, str] = {
    CODIGO_GLU_BASAL: "70–99 mg/dL",
    CODIGO_GLU_120: "Menor de 140 mg/dL",
}
