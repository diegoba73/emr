import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internacion", "0004_internacion_episodio_clinico"),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoDieta",
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
                    "nombre",
                    models.CharField(max_length=80, unique=True, verbose_name="Nombre"),
                ),
                (
                    "descripcion",
                    models.TextField(blank=True, null=True, verbose_name="Descripción"),
                ),
                (
                    "activo",
                    models.BooleanField(default=True, verbose_name="Activo"),
                ),
            ],
            options={
                "verbose_name": "Tipo de dieta",
                "verbose_name_plural": "Tipos de dieta",
                "ordering": ["nombre"],
            },
        ),
        migrations.AddField(
            model_name="internacion",
            name="tipo_dieta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="internaciones",
                to="internacion.tipodieta",
                verbose_name="Tipo de dieta",
            ),
        ),
    ]
