from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movil', '0002_paquetes_favoritos_lab'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordatorioturno',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('ASISTENCIA', 'Confirmar asistencia'),
                    ('CONFIRMAR_TURNO', 'Confirmar turno'),
                ],
                default='ASISTENCIA',
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='recordatorioturno',
            name='recordatorio_turno_dispositivo_fecha',
        ),
        migrations.AddConstraint(
            model_name='recordatorioturno',
            constraint=models.UniqueConstraint(
                fields=('turno', 'dispositivo', 'fecha_turno', 'tipo'),
                name='recordatorio_turno_dispositivo_fecha_tipo',
            ),
        ),
    ]
