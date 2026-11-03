from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0010_secretaria_lab'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='sedes',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[('CEHTA', 'CEHTA'), ('ICPL', 'ICPL')],
                    max_length=10,
                ),
                blank=True,
                default=list,
                help_text='CEHTA y/o ICPL. Vacío = acceso a ambas (sin filtro).',
                size=None,
                verbose_name='Sedes',
            ),
        ),
    ]
