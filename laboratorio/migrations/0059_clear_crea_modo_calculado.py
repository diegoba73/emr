# CLEAR_CREA: modo CALCULADO + defaults de entrada (clearance derivado)

from decimal import Decimal

from django.db import migrations

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO


def aplicar_clear_crea_calculado(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    row = ENTRADA_DEFAULTS_POR_CODIGO.get("CLEAR_CREA")
    if not row:
        return
    modo, dec, mult, fmt = row
    TipoExamen.objects.filter(codigo="CLEAR_CREA").update(
        modo_entrada=modo,
        ticket_decimales=dec,
        multiplicador_clinico=Decimal(mult),
        formato_informe_entrada=fmt or "",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0058_suero_quimica_y_tubo_eritro"),
    ]

    operations = [
        migrations.RunPython(aplicar_clear_crea_calculado, migrations.RunPython.noop),
    ]
