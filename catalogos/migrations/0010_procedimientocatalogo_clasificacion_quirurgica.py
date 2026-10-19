# Generated manually for Etapa A1 — clasificación quirúrgica aditiva.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogos", "0009_remove_procedimiento"),
    ]

    operations = [
        migrations.AddField(
            model_name="procedimientocatalogo",
            name="clasificacion_quirurgica",
            field=models.CharField(
                choices=[
                    ("SIN_ASIGNAR", "Sin asignar"),
                    ("NO_QUIRURGICO", "No quirúrgico"),
                    ("QUIRURGICO", "Quirúrgico"),
                ],
                db_index=True,
                default="SIN_ASIGNAR",
                max_length=20,
                verbose_name="Clasificación quirúrgica",
            ),
        ),
    ]
