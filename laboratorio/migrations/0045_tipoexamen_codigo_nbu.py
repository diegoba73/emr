from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0044_instrumentos_analizadores"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="codigo_nbu",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "Código del Nomenclador Bioquímico Único (CUBRA). "
                    "Es distinto del código interno/IACA del campo «código»."
                ),
                max_length=20,
                null=True,
                verbose_name="Código NBU",
            ),
        ),
    ]
