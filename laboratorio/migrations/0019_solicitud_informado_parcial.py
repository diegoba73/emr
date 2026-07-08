"""Estado INFORMADO_PARCIAL para órdenes con resultados incompletos informados."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0018_tipo_examen_modo_entrada"),
    ]

    operations = [
        migrations.AlterField(
            model_name="solicitudexamen",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("EN_PROCESO", "En Proceso"),
                    ("INFORMADO_PARCIAL", "Informado parcialmente"),
                    ("FINALIZADO", "Finalizado"),
                ],
                default="PENDIENTE",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
    ]
