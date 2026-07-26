# Generated manually for QC Wiener/CM260 calibraciones

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0027_solicitud_listo_para_validar"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipoanalizador",
            name="marca_modelo",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="materialcontrol",
            name="marca",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="materialcontrol",
            name="producto",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="materialcontrol",
            name="nivel",
            field=models.CharField(
                choices=[
                    ("N1", "S1 (normal)"),
                    ("N2", "S2 (patológico)"),
                    ("N3", "Nivel 3"),
                ],
                default="N1",
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name="calibracion",
            name="calibrador_nombre",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="calibracion",
            name="marca",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="calibracion",
            name="codigo_lote",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="calibracion",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("PUNTO_UNICO", "Punto único"),
                    ("CURVA_MULTIPUNTO", "Curva multipunto"),
                ],
                default="PUNTO_UNICO",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="calibracion",
            name="puntos_curva",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="calibracion",
            name="tipo_examen",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="calibraciones_qc",
                to="laboratorio.tipoexamen",
            ),
        ),
    ]
