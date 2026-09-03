# Generated manually: equipo por examen + material QC
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0037_lab_protocolo_unificado"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="equipo_analizador",
            field=models.ForeignKey(
                blank=True,
                help_text="Analizador donde se procesa esta determinación (CM260, Sysmex, etc.).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tipos_examen",
                to="laboratorio.equipoanalizador",
                verbose_name="Equipo analizador",
            ),
        ),
        migrations.AddField(
            model_name="materialcontrol",
            name="equipo",
            field=models.ForeignKey(
                blank=True,
                help_text="Equipo al que pertenece este material de control (IQC).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="materiales_control",
                to="laboratorio.equipoanalizador",
            ),
        ),
    ]
