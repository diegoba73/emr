"""Actualiza label de INFORMADO_PARCIAL a «Informe parcial»."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0062_orinas_24h_modo_calculado"),
    ]

    operations = [
        migrations.AlterField(
            model_name="solicitudexamen",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("EN_PROCESO", "En Proceso"),
                    ("INFORMADO_PARCIAL", "Informe parcial"),
                    ("LISTO_PARA_VALIDAR", "Listo para validar"),
                    ("FINALIZADO", "Finalizado"),
                ],
                default="PENDIENTE",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
    ]
