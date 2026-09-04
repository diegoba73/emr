"""Estado administrativo de obra social en órdenes LIMS (lab y microbiología)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0039_producto_control_hibrido"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="estado_obra_social",
            field=models.CharField(
                blank=True,
                choices=[
                    ("AUTORIZADO", "Autorizado"),
                    ("DEBE_ORDEN", "Debe orden"),
                    ("FALTA_AUTORIZACION", "Falta autorización"),
                    ("DEBE_ABONAR", "Debe abonar"),
                ],
                default="",
                help_text="Situación de cobertura: autorizado, debe orden, falta autorización o debe abonar.",
                max_length=24,
                verbose_name="Estado obra social",
            ),
        ),
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="estado_obra_social",
            field=models.CharField(
                blank=True,
                choices=[
                    ("AUTORIZADO", "Autorizado"),
                    ("DEBE_ORDEN", "Debe orden"),
                    ("FALTA_AUTORIZACION", "Falta autorización"),
                    ("DEBE_ABONAR", "Debe abonar"),
                ],
                default="",
                help_text="Situación de cobertura: autorizado, debe orden, falta autorización o debe abonar.",
                max_length=24,
                verbose_name="Estado obra social",
            ),
        ),
    ]
