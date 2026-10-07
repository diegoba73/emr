# Reintroduce estado CANCELADO en SolicitudExamen + campos de auditoría de cancelación.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("laboratorio", "0067_renombrar_cultivos_cateter_retrocultivo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="solicitudexamen",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("EN_PROCESO", "En Proceso"),
                    ("INFORMADO_PARCIAL", "Informe parcial"),
                    ("LISTO_PARA_VALIDAR", "Listo para validar"),
                    ("FINALIZADO", "Finalizado"),
                    ("CANCELADO", "Cancelado"),
                ],
                default="PENDIENTE",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="cancelado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="solicitudes_examen_canceladas",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Cancelado por",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="fecha_cancelacion",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de cancelación",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="motivo_cancelacion",
            field=models.TextField(
                blank=True,
                default="",
                verbose_name="Motivo de cancelación",
            ),
        ),
    ]
