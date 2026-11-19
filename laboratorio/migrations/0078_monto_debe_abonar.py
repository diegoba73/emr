"""Monto opcional a abonar cuando estado_obra_social es DEBE_ABONAR."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0077_tipoexamen_campos_detalle_tabla_interpretacion"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="monto_debe_abonar",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Importe que debe abonar el paciente cuando estado_obra_social es DEBE_ABONAR.",
                max_digits=12,
                null=True,
                verbose_name="Monto a abonar",
            ),
        ),
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="monto_debe_abonar",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Importe que debe abonar el paciente cuando estado_obra_social es DEBE_ABONAR.",
                max_digits=12,
                null=True,
                verbose_name="Monto a abonar",
            ),
        ),
    ]
