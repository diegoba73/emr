# C — vínculo sesión→Atencion e informe→RegistroProcedimiento (aditivo)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('turnos', '0010_turno_asistencia_confirmada_en'),
        ('estudios', '0008_historial_turno_sesion_b'),
    ]

    operations = [
        migrations.AddField(
            model_name='sesionactividad',
            name='atencion',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sesiones_actividad',
                to='turnos.atencion',
            ),
        ),
        migrations.AddField(
            model_name='informeestudiocomplementario',
            name='registro_procedimiento',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='informes_estudio_complementario',
                to='turnos.registroprocedimiento',
            ),
        ),
    ]
