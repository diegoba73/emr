from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0010_medico_email_telefono'),
        ('estudios', '0011_cirugia_catalogo_jerarquico'),
    ]

    operations = [
        migrations.AddField(
            model_name='estudiocomplementario',
            name='anestesista_previsto',
            field=models.ForeignKey(
                blank=True,
                help_text='Solo CIRUGIA: anestesista previsto en el alta (confirmable al realizar).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='estudios_anestesista_previsto',
                to='medicos.medico',
            ),
        ),
        migrations.AlterField(
            model_name='estudiocomplementario',
            name='medico_solicitante',
            field=models.ForeignKey(
                blank=True,
                help_text='Profesional previsto (estudio/procedimiento) o cirujano (CIRUGIA).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='estudios_solicitados',
                to='medicos.medico',
            ),
        ),
    ]
