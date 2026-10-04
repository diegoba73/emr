# Asegura TipoCultivoMicrobiologia HISOPADO_ANAL (pedido papel micro).

from django.db import migrations


def seed_hisopado_anal(apps, schema_editor):
    from laboratorio.micro_catalogos_seed import seed_catalogos_microbiologia

    seed_catalogos_microbiologia(update_existing=True)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0060_orden_numero_ascendente"),
    ]

    operations = [
        migrations.RunPython(seed_hisopado_anal, migrations.RunPython.noop),
    ]
