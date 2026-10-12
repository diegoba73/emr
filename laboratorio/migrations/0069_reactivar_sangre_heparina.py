"""Reactiva TipoMuestra SANGRE_HEPARINA (CA_ION / LACT / gases no-EAB).

Quedó inactiva en algunos entornos tras unificar química a SUERO; sigue siendo
la muestra canónica de heparina venosa para lactato y calcio iónico.
"""

from django.db import migrations


def reactivar_sangre_heparina(apps, schema_editor):
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")
    TipoMuestra.objects.filter(codigo="SANGRE_HEPARINA").update(activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0068_solicitud_cancelado"),
    ]

    operations = [
        migrations.RunPython(reactivar_sangre_heparina, migrations.RunPython.noop),
    ]
