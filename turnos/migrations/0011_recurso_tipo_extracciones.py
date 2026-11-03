from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('turnos', '0010_turno_asistencia_confirmada_en'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurso',
            name='tipo_recurso',
            field=models.CharField(
                choices=[
                    ('CONSULTORIO', 'Consultorio Ambulatorio'),
                    ('GUARDIA', 'Guardia'),
                    ('SALA_PROCEDIMIENTO', 'Sala de Procedimiento/Estudio'),
                    ('SALA_HEMODINAMIA', 'Sala de Hemodinamia'),
                    ('QUIROFANO', 'Quirófano'),
                    ('EXTRACCIONES', 'Extracciones / toma de muestra'),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
    ]
