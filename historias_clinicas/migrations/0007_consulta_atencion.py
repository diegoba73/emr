import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("historias_clinicas", "0006_add_performance_indexes"),
        ("turnos", "0008_atencion_contexto_internacion_evolucion"),
    ]

    operations = [
        migrations.AddField(
            model_name="consulta",
            name="atencion",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="consulta_hc",
                to="turnos.atencion",
                verbose_name="Atención asociada",
            ),
        ),
    ]
