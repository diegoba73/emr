from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('turnos', '0015_turno_origen'),
    ]

    operations = [
        migrations.AddField(
            model_name='turno',
            name='requiere_aceptacion_paciente',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    'True cuando secretaría/admin reprogramó el turno y el paciente '
                    'aún no aceptó ni rechazó el nuevo horario.'
                ),
            ),
        ),
    ]
