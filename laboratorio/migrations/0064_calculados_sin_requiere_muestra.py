# Exámenes CALCULADO (clearance, LDL, orinas 24 hs, etc.) no exigen tubo propio.

from django.db import migrations


def quitar_requiere_muestra_calculados(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoExamen.objects.filter(modo_entrada="CALCULADO", requiere_muestra=True).update(
        requiere_muestra=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0063_informe_parcial_label"),
    ]

    operations = [
        migrations.RunPython(quitar_requiere_muestra_calculados, migrations.RunPython.noop),
    ]
