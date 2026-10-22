# TFG: filtrado glomerular estimado CKD-EPI 2021 (CALCULADO, sin tubo)

from decimal import Decimal

from django.db import migrations

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO


def aplicar_tfg(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")
    row = ENTRADA_DEFAULTS_POR_CODIGO.get("TFG")
    if not row:
        return
    modo, dec, mult, fmt = row
    suero, _ = TipoMuestra.objects.get_or_create(
        codigo="SUERO",
        defaults={"nombre": "Suero", "color_tubo": "Rojo", "activo": True},
    )
    defaults = {
        "nombre": "Filtrado glomerular (CKD-EPI)",
        "abreviatura": "eGFR",
        "tipo_resultado": "NUMERICO",
        "modo_entrada": modo,
        "ticket_decimales": dec,
        "multiplicador_clinico": Decimal(mult),
        "formato_informe_entrada": fmt or "",
        "requiere_muestra": False,
        "tipo_contenedor": None,
        "activo": True,
        "unidad_default": "mL/min/1.73 m²",
        "metodo": "Calculado CKD-EPI 2021 (creatinina)",
        "rango_referencia_texto": "≥ 60 mL/min/1.73 m²",
        "rango_min": Decimal("60"),
        "tipo_muestra_requerida": suero,
    }
    TipoExamen.objects.update_or_create(codigo="TFG", defaults=defaults)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0072_estudiomicro_examen_fresco"),
    ]

    operations = [
        migrations.RunPython(aplicar_tfg, migrations.RunPython.noop),
    ]
