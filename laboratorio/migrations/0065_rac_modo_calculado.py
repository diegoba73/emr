# RAC: modo CALCULADO + sin tubo propio (relación albúmina/creatinina)

from decimal import Decimal

from django.db import migrations

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO


def aplicar_rac_calculado(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    row = ENTRADA_DEFAULTS_POR_CODIGO.get("RAC")
    if not row:
        return
    modo, dec, mult, fmt = row
    TipoExamen.objects.filter(codigo="RAC").update(
        modo_entrada=modo,
        ticket_decimales=dec,
        multiplicador_clinico=Decimal(mult),
        formato_informe_entrada=fmt or "",
        requiere_muestra=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0064_calculados_sin_requiere_muestra"),
    ]

    operations = [
        migrations.RunPython(aplicar_rac_calculado, migrations.RunPython.noop),
    ]
