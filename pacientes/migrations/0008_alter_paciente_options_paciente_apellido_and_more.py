"""Reescritura segura.

El nombre del archivo se conserva intencionalmente porque otras apps en ramas
de trabajo paralelas (notablemente ``turnos`` en sus migraciones
0005/0006/0007) declaran dependencia hacia este label exacto. Renombrarlo
rompería esas cadenas. El contenido de esta migración es no destructivo y se
limita a fijar el ``Meta.ordering`` del modelo ``Paciente`` en
``['apellido', 'nombre']``, que es el orden que asume el resto del sistema
una vez que ``Paciente`` queda como fuente de verdad de los datos personales.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0007_remove_duplicate_fields"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="paciente",
            options={
                "ordering": ["apellido", "nombre"],
                "verbose_name": "Paciente",
                "verbose_name_plural": "Pacientes",
            },
        ),
    ]
