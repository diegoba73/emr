from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0010_medico_email_telefono'),
    ]

    operations = [
        migrations.AddField(
            model_name='medico',
            name='sedes',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[('CEHTA', 'CEHTA'), ('ICPL', 'ICPL')],
                    max_length=10,
                ),
                blank=True,
                default=list,
                help_text='CEHTA y/o ICPL. Vacío = visible en todas las sedes.',
                size=None,
                verbose_name='Sedes',
            ),
        ),
    ]
