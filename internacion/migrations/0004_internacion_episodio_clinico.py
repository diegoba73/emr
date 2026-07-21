import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internacion", "0003_internacion_diagnostico_cie_and_more"),
        ("turnos", "0007_registroprocedimiento_estudio"),
    ]

    operations = [
        migrations.AddField(
            model_name="internacion",
            name="numero_internacion",
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                unique=True,
                verbose_name="Número de Internación",
            ),
        ),
        migrations.AddField(
            model_name="internacion",
            name="atencion_origen",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="internaciones_derivadas",
                to="turnos.atencion",
                verbose_name="Atención de origen",
            ),
        ),
        migrations.AddField(
            model_name="internacion",
            name="motivo_ingreso",
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="Motivo de Ingreso",
            ),
        ),
    ]
