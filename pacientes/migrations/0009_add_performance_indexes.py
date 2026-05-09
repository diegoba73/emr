"""Índices de performance sobre ``Paciente``.

Crea índices secundarios sobre ``apellido`` y ``nombre`` para acelerar
búsquedas y listados ordenados por apellido. No modifica datos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0008_alter_paciente_options_paciente_apellido_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="paciente",
            index=models.Index(fields=["apellido"], name="paciente_apellido_idx"),
        ),
        migrations.AddIndex(
            model_name="paciente",
            index=models.Index(fields=["nombre"], name="paciente_nombre_idx"),
        ),
    ]
