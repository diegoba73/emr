from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('turnos', '0016_turno_requiere_aceptacion_paciente'),
    ]

    operations = [
        migrations.AddField(
            model_name='turno',
            name='reprogramaciones_paciente',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Cantidad de reprogramaciones hechas por el paciente sobre esta cadena de turnos.',
            ),
        ),
    ]
