"""Agrega vínculo opcional ArchivoMedico → Atencion."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('turnos', '0007_registroprocedimiento_estudio'),
        ('archivos_medicos', '0005_alter_archivomedico_archivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivomedico',
            name='atencion',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='archivos_medicos',
                to='turnos.atencion',
                verbose_name='Atención Asociada',
            ),
        ),
    ]
