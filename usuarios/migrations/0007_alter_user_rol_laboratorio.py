# Generated manually for role choice `laboratorio`

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_alter_user_rol_alter_user_telefono'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='rol',
            field=models.CharField(
                choices=[
                    ('paciente', 'Paciente'),
                    ('medico', 'Médico'),
                    ('secretaria', 'Secretaria'),
                    ('enfermeria', 'Enfermería'),
                    ('laboratorio', 'Laboratorio'),
                    ('admin', 'Administrador'),
                ],
                default='paciente',
                max_length=20,
            ),
        ),
    ]
