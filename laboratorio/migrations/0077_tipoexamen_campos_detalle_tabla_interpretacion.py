from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0076_rar_modo_calculado"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="campos_detalle",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Lista ordenada de {etiqueta, valor} del catálogo para imprimir "
                    "(ej. Alergeno). Vacío = no se imprime nada extra."
                ),
                verbose_name="Campos de detalle (informe)",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="tabla_interpretacion",
            field=models.JSONField(
                blank=True,
                help_text=(
                    "Tabla configurable {titulo?, columnas[], filas[][]} para el informe. "
                    "Null/vacío = sin tabla."
                ),
                null=True,
                verbose_name="Tabla de interpretación",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="campos_detalle_snapshot",
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name="Campos de detalle (snapshot)",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="tabla_interpretacion_snapshot",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name="Tabla de interpretación (snapshot)",
            ),
        ),
    ]
