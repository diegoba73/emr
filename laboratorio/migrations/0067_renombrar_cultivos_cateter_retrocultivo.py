# Renombra etiquetas: CATETER → «Cultivo de punta de catéter»,
# PUNTA_CATETER → «Retrocultivo» (mismos códigos; no toca FKs).

from django.db import migrations


def seed_nombres_cultivo(apps, schema_editor):
    from laboratorio.micro_catalogos_seed import seed_catalogos_microbiologia

    seed_catalogos_microbiologia(update_existing=True)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0066_obra_social_orden_snapshot"),
    ]

    operations = [
        migrations.RunPython(seed_nombres_cultivo, migrations.RunPython.noop),
    ]
