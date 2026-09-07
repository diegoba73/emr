"""
Migración aditiva: snapshot de lugar de extracción en Muestra.

Justificación: ``ubicacion_actual`` cambia con recibir/conservar/cambiar-ubicacion
y no puede usarse como lugar histórico de la toma impresa en la etiqueta.
Nullable, sin backfill, sin RunPython destructivo.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0042_insumo_presentacion_caja"),
    ]

    operations = [
        migrations.AddField(
            model_name="muestra",
            name="lugar_extraccion",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Lugar histórico de la toma física. Inmutable tras registrarse. "
                    "Distinto de ubicacion_actual (custodia posterior)."
                ),
                max_length=120,
                null=True,
                verbose_name="Lugar de extracción",
            ),
        ),
    ]
