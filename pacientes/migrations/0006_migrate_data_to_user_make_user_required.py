"""Reescritura segura.

El nombre original de este archivo correspondía a una migración previa que
movía datos personales del Paciente a User/UserProfile, hacía obligatoria la
relación ``Paciente.user`` y creaba usuarios automáticamente con una password
literal. Esa estrategia fue descartada porque:

- Producía pérdida de datos personales en BD reales.
- Generaba usuarios con password fija (riesgo de seguridad inaceptable).
- Dejaba dos fuentes de verdad inconsistentes (Paciente vs User/UserProfile).

La nueva versión es no destructiva y se limita a ajustar la cardinalidad de la
relación con ``User`` y los choices del campo ``sexo``. No crea usuarios, no
ejecuta ``RunPython`` ni mueve datos personales fuera de Paciente.

El nombre del archivo se conserva intencionalmente para no romper migraciones
externas (por ejemplo ``turnos`` en su rama de trabajo) que declaren
dependencia hacia este label.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "pacientes",
            "0005_paciente_apellido_paciente_direccion_paciente_email_and_more",
        ),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="paciente",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="paciente",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Usuario del Sistema",
            ),
        ),
        migrations.AlterField(
            model_name="paciente",
            name="sexo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("M", "Masculino"),
                    ("F", "Femenino"),
                    ("O", "Otro"),
                ],
                max_length=1,
                null=True,
                verbose_name="Sexo",
            ),
        ),
    ]
