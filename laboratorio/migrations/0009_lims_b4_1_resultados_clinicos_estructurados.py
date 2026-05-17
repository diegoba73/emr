# B4.1 — Resultados clínicos estructurados (TipoExamen + ResultadoExamen)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0008_lims_b3_4_microbiologia_informes"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="seccion",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tipos_examen",
                to="laboratorio.seccionlaboratorio",
                verbose_name="Sección",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="tipo_resultado",
            field=models.CharField(
                choices=[
                    ("TEXTO", "Texto"),
                    ("NUMERICO", "Numérico"),
                    ("CUALITATIVO", "Cualitativo"),
                ],
                default="TEXTO",
                max_length=32,
                verbose_name="Tipo de resultado",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="unidad_default",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
                verbose_name="Unidad por defecto",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="rango_min",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Rango mínimo",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="rango_max",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Rango máximo",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="valor_critico_min",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Valor crítico mínimo",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="valor_critico_max",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Valor crítico máximo",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="permite_resultado_texto",
            field=models.BooleanField(
                default=True,
                verbose_name="Permite resultado textual",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="valor_numerico",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=14,
                null=True,
                verbose_name="Valor numérico",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="unidad",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
                verbose_name="Unidad",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="rango_referencia_snapshot",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Rango referencia (snapshot)",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="rango_min_snapshot",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Rango mínimo (snapshot)",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="rango_max_snapshot",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Rango máximo (snapshot)",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="es_critico",
            field=models.BooleanField(default=False, verbose_name="Es crítico"),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="valor_critico_min_snapshot",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Crítico mínimo (snapshot)",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="valor_critico_max_snapshot",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Crítico máximo (snapshot)",
            ),
        ),
    ]
