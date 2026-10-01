from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internacion", "0008_vigencia_infraestructura"),
    ]

    operations = [
        migrations.AddField(
            model_name="internacion",
            name="dieta_texto",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Texto libre cuando la dieta no está en el catálogo, o nota adicional.",
                max_length=120,
                verbose_name="Dieta (texto)",
            ),
        ),
    ]
