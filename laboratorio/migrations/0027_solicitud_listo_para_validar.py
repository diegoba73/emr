"""Estado LISTO_PARA_VALIDAR: resultados completos pendientes de validación bioquímica."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0026_inventario_y_qc"),
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
                    ("LISTO_PARA_VALIDAR", "Listo para validar"),
                    ("FINALIZADO", "Finalizado"),
                ],
                default="PENDIENTE",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
    ]
