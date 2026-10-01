# Generated manually for LecturaCultivo.recuento_bacteriano

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0054_estudiomicro_examen_orina"),
    ]

    operations = [
        migrations.AddField(
            model_name="lecturacultivo",
            name="recuento_bacteriano",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Ej. <10³ UFC/ml, ≥10⁵ UFC/ml (típico en urocultivo).",
                max_length=80,
                verbose_name="Recuento bacteriano",
            ),
        ),
    ]
