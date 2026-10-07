import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('medicos', '0008_medico_ambito_atencion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profesional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(blank=True, max_length=100, null=True, verbose_name='Nombre')),
                ('apellido', models.CharField(blank=True, max_length=100, null=True, verbose_name='Apellido')),
                ('matricula', models.CharField(max_length=50, unique=True, verbose_name='Matrícula / código')),
                ('fecha_registro', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')),
                ('ultima_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Última Actualización')),
                (
                    'especialidad',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='profesionales',
                        to='medicos.especialidad',
                        verbose_name='Especialidad',
                    ),
                ),
                (
                    'user',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='profesional',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Usuario del Sistema',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Profesional',
                'verbose_name_plural': 'Profesionales',
                'ordering': ['apellido', 'nombre'],
            },
        ),
    ]
