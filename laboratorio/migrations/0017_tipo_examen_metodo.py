from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0016_solicitud_informe_entrega_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="metodo",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Método utilizado para el análisis (ej: 'Enzimático colorimétrico').",
                max_length=120,
                verbose_name="Método analítico",
            ),
        ),
    ]
