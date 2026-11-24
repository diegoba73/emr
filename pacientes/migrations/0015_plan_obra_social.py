from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pacientes', '0014_obrasocial_catalogo'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='plan_obra_social',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Plan de la cobertura principal (obligatorio si no es PARTICULAR al reservar desde la app).',
                max_length=80,
                verbose_name='Plan de obra social',
            ),
        ),
        migrations.AddField(
            model_name='pacienteafiliacion',
            name='plan',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Plan de la obra social (obligatorio para coberturas no PARTICULAR en reserva app).',
                max_length=80,
                verbose_name='Plan',
            ),
        ),
    ]
