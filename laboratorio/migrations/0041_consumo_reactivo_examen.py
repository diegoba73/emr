# Generated manually for reagent consumption recipes

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0040_estado_obra_social"),
    ]

    operations = [
        migrations.AddField(
            model_name="insumolab",
            name="proveedor",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="insumolab",
            name="composicion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SOLO_A", "Solo A"),
                    ("A_B", "A + B (mismo cartucho)"),
                    ("OTRO", "Otro"),
                ],
                default="",
                help_text="Informativo: cartucho solo A o A+B juntos (no duplica stock).",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="insumolab",
            name="canal_analizador",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DEDICADO", "Línea dedicada"),
                    ("ABIERTO", "Línea abierta"),
                ],
                default="",
                help_text="CM260: línea dedicada u abierta.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="insumolab",
            name="equipo",
            field=models.ForeignKey(
                blank=True,
                help_text="Equipo asociado (ej. CM260) para filtros de stock.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="insumos",
                to="laboratorio.equipoanalizador",
            ),
        ),
        migrations.AddField(
            model_name="movimientostock",
            name="resultado_id",
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text="ResultadoExamen que originó el egreso (idempotencia).",
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="ConsumoInsumoExamen",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "cantidad_por_determinacion",
                    models.DecimalField(
                        decimal_places=4,
                        default=1,
                        help_text="Unidades del insumo restadas por cada resultado cargado.",
                        max_digits=12,
                    ),
                ),
                (
                    "rol",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Etiqueta UI opcional (CARTUCHO, DILUYENTE, etc.).",
                        max_length=40,
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "insumo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consumos_examen",
                        to="laboratorio.insumolab",
                    ),
                ),
                (
                    "tipo_examen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consumos_insumo",
                        to="laboratorio.tipoexamen",
                    ),
                ),
            ],
            options={
                "verbose_name": "Consumo de insumo por examen",
                "verbose_name_plural": "Consumos de insumos por examen",
                "ordering": ["tipo_examen_id", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="consumoinsumoexamen",
            constraint=models.UniqueConstraint(
                fields=("tipo_examen", "insumo"),
                name="uniq_consumo_insumo_examen",
            ),
        ),
    ]
