# Generated manually for LIMS Fase A — rol bioquímico

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_roles_estudios_complementarios'),
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
