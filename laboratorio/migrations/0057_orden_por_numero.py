# AlterModelOptions: listados LIMS ordenan solo por numero.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0056_fecha_programada_toma"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="solicitudexamen",
            options={
                "ordering": ["-numero"],
                "verbose_name": "Solicitud de Examen",
                "verbose_name_plural": "Solicitudes de Examen",
            },
        ),
        migrations.AlterModelOptions(
            name="estudiomicrobiologia",
            options={
                "ordering": ["-numero"],
                "verbose_name": "Estudio de microbiología",
                "verbose_name_plural": "Estudios de microbiología",
            },
        ),
    ]
