# Rol secretaria_lab (aditivo). No remapea usuarios secretaria existentes.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_alter_user_rol_bioquimico'),
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
                    ('secretaria_lab', 'Secretaria laboratorio'),
                    ('enfermeria', 'Enfermería'),
                    ('laboratorio', 'Laboratorio'),
                    ('bioquimico', 'Bioquímico'),
                    ('kinesiologo', 'Kinesiólogo'),
                    ('radiologo', 'Radiólogo'),
                    ('ecografista', 'Ecografista'),
                    ('fonoaudiologo', 'Fonoaudiólogo'),
                    ('admin', 'Administrador'),
                ],
                default='paciente',
                max_length=20,
            ),
        ),
    ]
