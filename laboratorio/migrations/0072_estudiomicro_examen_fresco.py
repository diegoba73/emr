# Generated manually for examen_fresco on EstudioMicrobiologia

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0071_pedido_completo_idempotencia"),
    ]

    operations = [
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="examen_fresco",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Cultivos genitales (p. ej. vaginal/uretral): examen microscópico en fresco "
                    "y micológico directo de la misma muestra. Solo se informa si hay datos."
                ),
                verbose_name="Examen en fresco",
            ),
        ),
    ]
