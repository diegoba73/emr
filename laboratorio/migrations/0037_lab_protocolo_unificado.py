# Generated manually for LabProtocoloCounter + help_text updates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0036_micro_etiquetas_batch_consulta"),
    ]

    operations = [
        migrations.CreateModel(
            name="LabProtocoloCounter",
            fields=[
                ("year", models.PositiveIntegerField(primary_key=True, serialize=False, verbose_name="Año")),
                ("last_n", models.PositiveIntegerField(default=0, verbose_name="Último correlativo")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Contador de protocolo LAB",
                "verbose_name_plural": "Contadores de protocolo LAB",
            },
        ),
        migrations.AlterField(
            model_name="estudiomicrobiologia",
            name="codigo_barra",
            field=models.CharField(
                blank=True,
                help_text="Igual al número de protocolo (LAB-YYYY-XXXXX); se asigna al imprimir etiqueta.",
                max_length=32,
                null=True,
                unique=True,
                verbose_name="Código de barras",
            ),
        ),
        migrations.AlterField(
            model_name="estudiomicrobiologia",
            name="numero",
            field=models.CharField(
                blank=True,
                help_text="Generado automáticamente si se deja vacío (LAB-YYYY-XXXXX).",
                max_length=32,
                null=True,
                unique=True,
                verbose_name="Número de estudio",
            ),
        ),
        migrations.AlterField(
            model_name="muestra",
            name="codigo_barra",
            field=models.CharField(
                blank=True,
                help_text="Generado automáticamente si se deja vacío (LAB-YYYY-XXXXX-nn).",
                max_length=32,
                null=True,
                unique=True,
                verbose_name="Código de barras",
            ),
        ),
    ]
