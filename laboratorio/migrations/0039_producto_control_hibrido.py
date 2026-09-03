# Generated manually: producto multiparámetro + corrida híbrida
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0038_equipo_examen_iqc"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductoControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=40, unique=True)),
                ("nombre", models.CharField(max_length=200)),
                ("marca", models.CharField(blank=True, default="", max_length=120)),
                (
                    "modo",
                    models.CharField(
                        choices=[
                            ("MULTIPARAM", "Multiparámetro (producto + nivel)"),
                            ("POR_ENSAYO", "Por ensayo"),
                        ],
                        default="MULTIPARAM",
                        max_length=20,
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "equipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="productos_control",
                        to="laboratorio.equipoanalizador",
                    ),
                ),
            ],
            options={"ordering": ["equipo__codigo", "nombre"]},
        ),
        migrations.CreateModel(
            name="LoteProductoControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_lote", models.CharField(max_length=80)),
                ("vencimiento", models.DateField()),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lotes",
                        to="laboratorio.productocontrol",
                    ),
                ),
            ],
            options={"ordering": ["-vencimiento"], "unique_together": {("producto", "codigo_lote")}},
        ),
        migrations.CreateModel(
            name="TargetLoteControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "nivel",
                    models.CharField(
                        choices=[("N1", "S1 (normal)"), ("N2", "S2 (patológico)"), ("N3", "Nivel 3")],
                        max_length=5,
                    ),
                ),
                ("media_target", models.DecimalField(decimal_places=4, max_digits=12)),
                ("de_target", models.DecimalField(decimal_places=4, max_digits=12)),
                (
                    "lote",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="targets",
                        to="laboratorio.loteproductocontrol",
                    ),
                ),
                (
                    "tipo_examen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="targets_lote_control",
                        to="laboratorio.tipoexamen",
                    ),
                ),
            ],
            options={
                "ordering": ["tipo_examen__codigo", "nivel"],
                "unique_together": {("lote", "tipo_examen", "nivel")},
            },
        ),
        migrations.AddField(
            model_name="corridaqc",
            name="lote_producto",
            field=models.ForeignKey(
                blank=True,
                help_text="Lote de producto multiparámetro (Standatrol, etc.).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="corridas",
                to="laboratorio.loteproductocontrol",
            ),
        ),
        migrations.AddField(
            model_name="corridaqc",
            name="nivel",
            field=models.CharField(
                blank=True,
                choices=[("N1", "S1 (normal)"), ("N2", "S2 (patológico)"), ("N3", "Nivel 3")],
                default="",
                help_text="Nivel S1/S2 cuando la corrida es de producto multiparámetro.",
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name="corridaqc",
            name="lote_control",
            field=models.ForeignKey(
                blank=True,
                help_text="Lote de material por ensayo (VIDAS/Finecare / legado).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="corridas",
                to="laboratorio.lotecontrol",
            ),
        ),
        migrations.AddField(
            model_name="puntoqc",
            name="tipo_examen",
            field=models.ForeignKey(
                blank=True,
                help_text="Ensayo del punto (corridas multiparámetro).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="puntos_qc",
                to="laboratorio.tipoexamen",
            ),
        ),
    ]
