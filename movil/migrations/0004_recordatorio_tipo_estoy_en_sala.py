from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movil', '0003_recordatorio_tipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordatorioturno',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('ASISTENCIA', 'Confirmar asistencia'),
                    ('CONFIRMAR_TURNO', 'Confirmar turno'),
                    ('ESTOY_EN_SALA', 'Aviso estoy en sala (1 h)'),
                ],
                default='ASISTENCIA',
                max_length=20,
            ),
        ),
    ]
