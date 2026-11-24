from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('turnos', '0014_historialreprogramacionturno'),
    ]

    operations = [
        migrations.AddField(
            model_name='turno',
            name='origen',
            field=models.CharField(
                choices=[
                    ('SISTEMA', 'Sistema / online'),
                    ('TELEFONO', 'Teléfono'),
                    ('PRESENCIAL', 'Presencial'),
                ],
                db_index=True,
                default='SISTEMA',
                help_text='Cómo se agendó el turno: sistema/online, teléfono o presencial.',
                max_length=20,
                verbose_name='Origen de la reserva',
            ),
        ),
    ]
