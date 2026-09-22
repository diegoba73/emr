# Generated manually for Ticket A — REF comercial en inventario (no destructiva).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0048_diestro_a_erba_ec90"),
    ]

    operations = [
        migrations.AddField(
            model_name="insumolab",
            name="ref_comercial",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text=(
                    "Referencia del fabricante (ej. Wiener 1008149, Finecare W216). "
                    "Independiente del código interno SKU. Opcional; vacío en registros legacy."
                ),
                max_length=80,
                verbose_name="REF comercial",
            ),
        ),
    ]
