# A2: tipo_actividad, procedimiento_catalogo (PROTECT), snapshot, multi-sesión;
# practica nullable (solo EMR). Backfill idempotente.

import django.db.models.deletion
from django.db import migrations, models

import estudios.practicas_cehta


def backfill_tipo_actividad_estudio(apps, schema_editor):
    """Idempotente: no pisa filas PROCEDIMIENTO/CIRUGIA; solo normaliza ESTUDIO sin FK."""
    Estudio = apps.get_model('estudios', 'EstudioComplementario')
    # Nunca tocar tipos operativos futuros.
    qs = Estudio.objects.exclude(
        tipo_actividad__in=['PROCEDIMIENTO', 'CIRUGIA'],
    ).filter(procedimiento_catalogo_id__isnull=True)
    qs.update(
        tipo_actividad='ESTUDIO',
        clasificacion_quirurgica_snapshot=None,
        permite_multi_sesion=False,
    )


def noop_reverse(apps, schema_editor):
    # Conservador: no borrar columnas en reverse de datos.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalogos', '0010_procedimientocatalogo_clasificacion_quirurgica'),
        ('estudios', '0005_modalidad_to_practica'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estudiocomplementario',
            name='practica',
            field=models.CharField(
                blank=True,
                choices=estudios.practicas_cehta.PRACTICA_CHOICES,
                max_length=80,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='tipo_actividad',
            field=models.CharField(
                choices=[
                    ('ESTUDIO', 'Estudio'),
                    ('PROCEDIMIENTO', 'Procedimiento'),
                    ('CIRUGIA', 'Cirugía'),
                ],
                db_index=True,
                default='ESTUDIO',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='procedimiento_catalogo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='estudios_complementarios',
                to='catalogos.procedimientocatalogo',
            ),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='clasificacion_quirurgica_snapshot',
            field=models.CharField(
                blank=True,
                choices=[
                    ('NO_QUIRURGICO', 'No quirúrgico'),
                    ('QUIRURGICO', 'Quirúrgico'),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='permite_multi_sesion',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_tipo_actividad_estudio, noop_reverse),
    ]
