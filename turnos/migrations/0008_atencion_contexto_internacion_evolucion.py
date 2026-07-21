import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internacion", "0003_internacion_diagnostico_cie_and_more"),
        ("turnos", "0007_registroprocedimiento_estudio"),
    ]

    operations = [
        migrations.AddField(
            model_name="atencion",
            name="contexto_atencion",
            field=models.CharField(
                choices=[
                    ("AMBULATORIA", "Ambulatoria"),
                    ("INTERNACION", "Internación"),
                    ("GUARDIA", "Guardia"),
                ],
                db_index=True,
                default="AMBULATORIA",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="atencion",
            name="internacion",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="atenciones",
                to="internacion.internacion",
            ),
        ),
        migrations.CreateModel(
            name="EvolucionInternacion",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, null=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, null=True),
                ),
                (
                    "atencion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="evolucion_internacion",
                        serialize=False,
                        to="turnos.atencion",
                    ),
                ),
                (
                    "tipo_evolucion",
                    models.CharField(
                        choices=[
                            ("EVOLUCION_DIARIA", "Evolución diaria"),
                            ("INTERCONSULTA", "Interconsulta"),
                            ("NOTA_ENFERMERIA", "Nota de enfermería"),
                        ],
                        db_index=True,
                        default="EVOLUCION_DIARIA",
                        max_length=30,
                    ),
                ),
                (
                    "fecha_evolucion",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("subjetivo", models.TextField(blank=True, null=True)),
                ("objetivo", models.TextField(blank=True, null=True)),
                ("analisis", models.TextField(blank=True, null=True)),
                ("plan", models.TextField(blank=True, null=True)),
                ("signos_vitales_resumen", models.TextField(blank=True, null=True)),
                ("diagnostico_actualizado", models.TextField(blank=True, null=True)),
                ("plan_manejo", models.TextField(blank=True, null=True)),
                ("observaciones", models.TextField(blank=True, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
