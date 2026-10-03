# AlterModelOptions: listados LIMS ordenan por numero ascendente (primero → último).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0059_clear_crea_modo_calculado"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="solicitudexamen",
            options={
                "ordering": ["numero"],
                "verbose_name": "Solicitud de Examen",
                "verbose_name_plural": "Solicitudes de Examen",
            },
        ),
        migrations.AlterModelOptions(
            name="estudiomicrobiologia",
            options={
                "ordering": ["numero"],
                "verbose_name": "Estudio de microbiología",
                "verbose_name_plural": "Estudios de microbiología",
            },
        ),
    ]
