"""Orígenes ambulatorio externo CEHTA / ICPL."""

from django.db import migrations, models


def migrar_externo_papel_a_externo_cehta(apps, schema_editor):
    SolicitudExamen = apps.get_model('laboratorio', 'SolicitudExamen')
    SolicitudExamen.objects.filter(
        origen_solicitud='AMBULATORIO_CEHTA',
        medico_externo_nombre__gt='',
    ).update(origen_solicitud='EXTERNO_CEHTA')


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0021_origen_clinico_solicitud'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitudexamen',
            name='origen_solicitud',
            field=models.CharField(
                choices=[
                    ('INTERNACION_UCO', 'Internación — UCO'),
                    ('INTERNACION_UCE', 'Internación — UCE'),
                    ('GUARDIA', 'Guardia'),
                    ('AMBULATORIO_CEHTA', 'Ambulatorio — CEHTA'),
                    ('AMBULATORIO_ICPL', 'Ambulatorio — ICPL'),
                    ('EXTERNO_CEHTA', 'Ambulatorio externo — CEHTA'),
                    ('EXTERNO_ICPL', 'Ambulatorio externo — ICPL'),
                ],
                default='AMBULATORIO_CEHTA',
                max_length=24,
                verbose_name='Origen clínico',
            ),
        ),
        migrations.RunPython(migrar_externo_papel_a_externo_cehta, migrations.RunPython.noop),
    ]
