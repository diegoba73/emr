# Generated manually for sobreturnos (secretaría).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('turnos', '0012_sync_pending_indexes_tipo_atencion'),
    ]

    operations = [
        migrations.AddField(
            model_name='turno',
            name='es_sobreturno',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
