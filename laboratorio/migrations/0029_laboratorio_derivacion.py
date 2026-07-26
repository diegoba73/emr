# Derivación LAC / IACA

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0028_qc_calibracion_curva"),
    ]

    operations = [
        migrations.CreateModel(
            name="LaboratorioDerivacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=20, unique=True, verbose_name="Código")),
                ("nombre", models.CharField(max_length=200, verbose_name="Nombre")),
                ("ciudad", models.CharField(blank=True, default="", max_length=120, verbose_name="Ciudad")),
                ("acepta_sangre", models.BooleanField(default=False, verbose_name="Acepta sangre")),
                ("acepta_orina", models.BooleanField(default=False, verbose_name="Acepta orina")),
                ("acepta_cultivo", models.BooleanField(default=False, verbose_name="Acepta cultivos")),
                (
                    "acepta_cualquier",
                    models.BooleanField(
                        default=False,
                        help_text="Si está activo, no se restringe por tipo de muestra.",
                        verbose_name="Acepta cualquier muestra",
                    ),
                ),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Laboratorio de derivación",
                "verbose_name_plural": "Laboratorios de derivación",
                "ordering": ["codigo"],
            },
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="laboratorio_derivacion",
            field=models.ForeignKey(
                blank=True,
                help_text="Si está vacío, el examen se procesa en el laboratorio propio.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tipos_examen",
                to="laboratorio.laboratorioderivacion",
                verbose_name="Laboratorio de derivación",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="laboratorio_derivacion",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resultados",
                to="laboratorio.laboratorioderivacion",
                verbose_name="Laboratorio de derivación",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="estado_derivacion",
            field=models.CharField(
                choices=[
                    ("LOCAL", "Local (lab propio)"),
                    ("PENDIENTE_ENVIO", "Pendiente de envío"),
                    ("ENVIADO", "Enviado a lab externo"),
                    ("RESULTADO_RECIBIDO", "Resultado externo cargado"),
                ],
                default="LOCAL",
                max_length=24,
                verbose_name="Estado de derivación",
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="fecha_envio_derivacion",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Fecha de envío a lab externo"
            ),
        ),
        migrations.AddField(
            model_name="resultadoexamen",
            name="observaciones_derivacion",
            field=models.TextField(
                blank=True, default="", verbose_name="Observaciones de derivación"
            ),
        ),
    ]
