import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("turnos", "0008_atencion_contexto_internacion_evolucion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="atencion",
            name="tipo_atencion",
            field=models.CharField(
                choices=[
                    ("CONSULTORIO", "Consultorio Ambulatorio"),
                    ("GUARDIA", "Guardia"),
                    ("SALA_PROCEDIMIENTO", "Sala de Procedimiento/Estudio"),
                    ("SALA_HEMODINAMIA", "Sala de Hemodinamia"),
                    ("QUIROFANO", "Quirófano"),
                    ("INTERNACION", "Internación"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="recurso",
            name="tipo_recurso",
            field=models.CharField(
                choices=[
                    ("CONSULTORIO", "Consultorio Ambulatorio"),
                    ("GUARDIA", "Guardia"),
                    ("SALA_PROCEDIMIENTO", "Sala de Procedimiento/Estudio"),
                    ("SALA_HEMODINAMIA", "Sala de Hemodinamia"),
                    ("QUIROFANO", "Quirófano"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
    ]
