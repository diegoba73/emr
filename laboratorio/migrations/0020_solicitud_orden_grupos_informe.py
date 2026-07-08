from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0019_solicitud_informado_parcial"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="orden_grupos_informe",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Lista de claves panel-{id} o resultado-{id} para el orden en el PDF.",
                verbose_name="Orden de grupos en informe",
            ),
        ),
    ]
