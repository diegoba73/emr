"""Origen clínico de órdenes LIMS — choices ampliados."""

from django.db import migrations, models


def migrar_origen_legacy(apps, schema_editor):
    SolicitudExamen = apps.get_model('laboratorio', 'SolicitudExamen')
    Consulta = apps.get_model('historias_clinicas', 'Consulta')
    mapping_simple = {
        'EMR': 'AMBULATORIO_CEHTA',
        'EXTERNO_PAPEL': 'AMBULATORIO_CEHTA',
        'GUARDIA': 'GUARDIA',
    }
    for sol in SolicitudExamen.objects.all().iterator():
        old = sol.origen_solicitud
        if old in mapping_simple and old != 'EMR':
            sol.origen_solicitud = mapping_simple[old]
            sol.save(update_fields=['origen_solicitud'])
            continue
        if old != 'EMR':
            continue
        nuevo = mapping_simple['EMR']
        if sol.consulta_hc_id:
            try:
                consulta = Consulta.objects.select_related('turno__recurso').get(pk=sol.consulta_hc_id)
                turno = getattr(consulta, 'turno', None)
                recurso = getattr(turno, 'recurso', None) if turno else None
                if recurso and 'GUARDIA' in (recurso.nombre or '').upper():
                    nuevo = 'GUARDIA'
                elif recurso and (recurso.ubicacion or '').upper() == 'ICPL':
                    nuevo = 'AMBULATORIO_ICPL'
            except Exception:
                pass
        sol.origen_solicitud = nuevo
        sol.save(update_fields=['origen_solicitud'])


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0020_solicitud_orden_grupos_informe'),
        ('historias_clinicas', '0006_add_performance_indexes'),
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
                ],
                default='AMBULATORIO_CEHTA',
                max_length=24,
                verbose_name='Origen clínico',
            ),
        ),
        migrations.RunPython(migrar_origen_legacy, migrations.RunPython.noop),
    ]
