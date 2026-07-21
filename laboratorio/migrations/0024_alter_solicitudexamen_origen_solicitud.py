"""Sync SolicitudExamen.origen_solicitud choices label (Guardia — ICPL)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0023_tipoexamen_tipo_contenedor"),
    ]

    operations = [
        migrations.AlterField(
            model_name="solicitudexamen",
            name="origen_solicitud",
            field=models.CharField(
                choices=[
                    ("INTERNACION_UCO", "Internación — UCO"),
                    ("INTERNACION_UCE", "Internación — UCE"),
                    ("GUARDIA", "Guardia — ICPL"),
                    ("AMBULATORIO_CEHTA", "Ambulatorio — CEHTA"),
                    ("AMBULATORIO_ICPL", "Ambulatorio — ICPL"),
                    ("EXTERNO_CEHTA", "Ambulatorio externo — CEHTA"),
                    ("EXTERNO_ICPL", "Ambulatorio externo — ICPL"),
                ],
                default="AMBULATORIO_CEHTA",
                max_length=24,
                verbose_name="Origen clínico",
            ),
        ),
    ]
