from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('historias_clinicas', '0006_add_performance_indexes'),
        ('laboratorio', '0012_tipo_examen_requiere_muestra'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudexamen',
            name='consulta_hc',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='solicitudes_laboratorio',
                to='historias_clinicas.consulta',
                verbose_name='Consulta asociada',
            ),
        ),
    ]
