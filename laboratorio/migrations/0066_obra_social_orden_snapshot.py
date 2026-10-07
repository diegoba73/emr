# Snapshot OS/afiliado en SolicitudExamen y EstudioMicrobiologia (solo adelante).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0065_rac_modo_calculado"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="obra_social_orden",
            field=models.CharField(
                blank=True,
                default="",
                help_text="OS registrada al crear el pedido. Vacío → fallback a la ficha del paciente.",
                max_length=100,
                verbose_name="Obra social (orden)",
            ),
        ),
        migrations.AddField(
            model_name="solicitudexamen",
            name="afiliado_orden",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Afiliado registrado al crear el pedido. Vacío → fallback a la ficha del paciente.",
                max_length=50,
                verbose_name="N° afiliado (orden)",
            ),
        ),
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="obra_social_orden",
            field=models.CharField(
                blank=True,
                default="",
                help_text="OS registrada al crear el pedido. Vacío → fallback a la ficha del paciente.",
                max_length=100,
                verbose_name="Obra social (orden)",
            ),
        ),
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="afiliado_orden",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Afiliado registrado al crear el pedido. Vacío → fallback a la ficha del paciente.",
                max_length=50,
                verbose_name="N° afiliado (orden)",
            ),
        ),
    ]
