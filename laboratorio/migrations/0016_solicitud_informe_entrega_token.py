"""Token opaco para descarga pública del informe LIMS."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0015_solicitud_envio_informe"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="informe_entrega_token",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                unique=True,
                verbose_name="Token descarga informe",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="informe_entrega_token_expira",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Expiración token descarga informe",
            ),
        ),
    ]
