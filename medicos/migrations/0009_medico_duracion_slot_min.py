from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0008_medico_ambito_atencion'),
    ]

    operations = [
        migrations.AddField(
            model_name='medico',
            name='duracion_slot_min',
            field=models.PositiveIntegerField(
                default=20,
                help_text='Intervalo de cada consulta/estudio en la agenda ambulatoria del médico.',
                verbose_name='Duración del turno (minutos)',
            ),
        ),
    ]
