"""Campos de seguimiento de envío de informe LIMS."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("laboratorio", "0014_solicitud_estados_simplificados"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="fecha_informe_enviado",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha envío informe",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="informe_enviado_email",
            field=models.BooleanField(
                default=False,
                verbose_name="Informe enviado por email",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="informe_enviado_whatsapp",
            field=models.BooleanField(
                default=False,
                verbose_name="Informe enviado por WhatsApp",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="informe_enviado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="solicitudes_lims_informe_enviado",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Informe enviado por",
            ),
        ),
    ]
