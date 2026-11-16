# RAR: modo CALCULADO + sin tubo propio (relación aldosterona/actividad de renina)

from decimal import Decimal

from django.db import migrations

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO


def aplicar_rar_calculado(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    row = ENTRADA_DEFAULTS_POR_CODIGO.get("RAR")
    if not row:
        return
    modo, dec, mult, fmt = row
    TipoExamen.objects.filter(codigo="RAR").update(
        modo_entrada=modo,
        ticket_decimales=dec,
        multiplicador_clinico=Decimal(mult),
        formato_informe_entrada=fmt or "",
        requiere_muestra=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0075_problema_clinico_y_dx_orden"),
    ]

    operations = [
        migrations.RunPython(aplicar_rar_calculado, migrations.RunPython.noop),
    ]
