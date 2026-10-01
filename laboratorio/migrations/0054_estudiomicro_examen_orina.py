# Generated manually for examen_orina on EstudioMicrobiologia

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0053_labwin_micro_catalogos_sync"),
    ]

    operations = [
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="examen_orina",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Solo urocultivo: resultados de tira reactiva y sedimento de la misma muestra. "
                    "No sustituye un pedido de orina completa en lab. clínico."
                ),
                verbose_name="Examen de orina (tira + sedimento)",
            ),
        ),
    ]
