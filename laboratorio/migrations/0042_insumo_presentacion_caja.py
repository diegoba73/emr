# Presentación de compra: cartuchos por caja + ml por envase/pack

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0041_consumo_reactivo_examen"),
    ]

    operations = [
        migrations.AddField(
            model_name="insumolab",
            name="unidades_por_caja",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Cuántos cartuchos/envases trae una caja al comprar (ej. 10).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="insumolab",
            name="volumen_por_unidad",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Volumen de cada cartucho/pack en ml (ej. 40). Packs hematología/EC90.",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="insumolab",
            name="unidad",
            field=models.CharField(
                default="u",
                help_text="Unidad en la que contás el stock: cartucho, ml, test, etc.",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="insumolab",
            name="canal_analizador",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DEDICADO", "Línea dedicada"),
                    ("ABIERTO", "Línea abierta"),
                ],
                default="",
                help_text="Línea del analizador si aplica (dedicada / abierta).",
                max_length=20,
            ),
        ),
    ]
