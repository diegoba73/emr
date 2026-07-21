"""Agrega TipoExamen.tipo_contenedor y siembra tubos estándar."""

from django.db import migrations, models
import django.db.models.deletion


CONTENEDORES_SEED = (
    ("EDTA", "Tubo EDTA", "Morado", "EDTA K2"),
    ("CITRATO", "Tubo Citrato", "Celeste", "Citrato de sodio"),
    ("HEPARINA", "Tubo Heparina", "Verde", "Heparina de litio"),
    ("SUERO", "Tubo Suero", "Rojo", "Sin anticoagulante / gel"),
)


def seed_contenedores(apps, schema_editor):
    TipoContenedor = apps.get_model("laboratorio", "TipoContenedor")
    for codigo, nombre, color, aditivo in CONTENEDORES_SEED:
        TipoContenedor.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "color": color,
                "aditivo": aditivo,
                "activo": True,
                "descripcion": "",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0022_origen_ambulatorio_externo"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="tipo_contenedor",
            field=models.ForeignKey(
                blank=True,
                help_text="Tubo físico requerido para la extracción (EDTA, Citrato, Heparina, Suero, etc.).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tipos_examen",
                to="laboratorio.tipocontenedor",
                verbose_name="Tipo de tubo / contenedor",
            ),
        ),
        migrations.RunPython(seed_contenedores, migrations.RunPython.noop),
    ]
