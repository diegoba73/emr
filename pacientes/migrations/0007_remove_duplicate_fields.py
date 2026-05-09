"""Reescritura segura.

El nombre original correspondía a una migración que eliminaba los campos
personales (``nombre``, ``apellido``, ``email``, ``telefono``,
``fecha_nacimiento``, ``sexo``, ``direccion``) del modelo ``Paciente``. Esa
operación implicaba pérdida total de los datos personales en BD productiva y
fue descartada en favor de mantener ``Paciente`` como fuente de verdad.

Esta versión no elimina ningún campo. Se limita a flexibilizar ``nombre`` y
``apellido`` para que admitan ``NULL`` y queden alineados con el modelo
declarado en ``pacientes.models``. El nombre del archivo se conserva para
preservar la cadena de dependencias que apps externas puedan haber declarado
en ramas de trabajo paralelas.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0006_migrate_data_to_user_make_user_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paciente",
            name="nombre",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Nombre"
            ),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="apellido",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Apellido"
            ),
        ),
    ]
