"""
Compatibilidad IACA ↔ catálogo operativo LIMS (paneles).

Reglas:
- Los productos IACA compuestos (Hemograma, Coagulograma, etc.) NO son TipoExamen
  solicitables: se desactivan y viven como PanelExamen (códigos PAN_* del formulario).
- Los analitos del panel se aseguran activos. Si el código IACA choca con un uso LIMS
  distinto (LEU=Leucina IACA vs leucocitos; CREA=TFG IACA vs creatininemia), se usa
  código operativo interno documentado aquí.
- IACA_CODIGO_PANEL: producto IACA → panel operativo.
"""
from __future__ import annotations

# Producto IACA (TipoExamen) → panel LIMS. Se desactivan como examen suelto.
IACA_PRODUCTO_A_PANEL: dict[str, str] = {
    "HEM": "PAN_HEMO",
    "COA": "PAN_COAG",
    "IONO": "PAN_IONO",
    "IONOO": "PAN_IONO_U",
    "IONO24": "PAN_IONO_U24",
    "IONOL": "PAN_IONO_U",  # orina litro → mismo panel urinario operativo
    "HEPATO": "PAN_HEP",
    "OC": "PAN_ORI",
    "PLIPI": "PAN_LIP",
    "PEL": "PAN_ELP",
    "PELLCR": "PAN_ELP",
    "LIPIE": "PAN_LIP",
    "CREAC24": "PAN_CLEAR",
}

# Códigos IACA compuestos extra (perfiles sin panel papel 1:1): solo desactivar como
# examen "caja negra" si no queremos pedirlos sueltos. Vacío = no tocar.
IACA_PRODUCTOS_COMPUESTOS_EXTRA: frozenset[str] = frozenset(
    {
        "HIERRST",  # Hierro + saturación (tenemos HIERR/SAT separados en panel férrico)
        "PSALT",  # PSA libre + total
    }
)

# Colisiones código IACA vs significado LIMS operativo
# IACA LEU = Leucina; leucocitos del hemograma = LEUCO
# IACA CREA = TFG; creatininemia = CREATI
CODIGO_OPERATIVO_LEUCOCITOS = "LEUCO"
CODIGO_OPERATIVO_CREATININEMIA = "CREATI"