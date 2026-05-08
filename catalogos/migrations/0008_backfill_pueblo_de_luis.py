# Generated manually — backfill defensivo ICPL → PUEBLO_DE_LUIS


from django.db import migrations


def forwards_icpl_to_pueblo(apps, schema_editor):
    CentroFisico = apps.get_model("catalogos", "CentroFisico")
    CentroFisico.objects.filter(codigo="ICPL").update(codigo="PUEBLO_DE_LUIS")


def backwards_noop(apps, schema_editor):
    """No revertir: podría confundir centros creados ya como PUEBLO_DE_LUIS."""


class Migration(migrations.Migration):

    dependencies = [
        ("catalogos", "0007_add_performance_indexes"),
    ]

    operations = [
        migrations.RunPython(forwards_icpl_to_pueblo, backwards_noop),
    ]
