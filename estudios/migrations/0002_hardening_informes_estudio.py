# C6.4.3 — único informe vigente por estudio (constraint parcial PostgreSQL)

from django.db import migrations, models
from django.db.models import Count, Q


def dedupe_informes_vigentes(apps, schema_editor):
    Informe = apps.get_model('estudios', 'InformeEstudioComplementario')
    dup_estudios = (
        Informe.objects.filter(es_vigente=True)
        .values('estudio_id')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
    )
    for row in dup_estudios:
        estudio_id = row['estudio_id']
        vigentes = list(
            Informe.objects.filter(estudio_id=estudio_id, es_vigente=True).order_by(
                '-version', '-id'
            )
        )
        keep = next(
            (inf for inf in vigentes if inf.estado == 'VALIDADO'),
            vigentes[0] if vigentes else None,
        )
        if keep is None:
            continue
        Informe.objects.filter(estudio_id=estudio_id, es_vigente=True).exclude(
            pk=keep.pk
        ).update(es_vigente=False)


class Migration(migrations.Migration):

    dependencies = [
        ('estudios', '0001_estudio_complementario_base'),
    ]

    operations = [
        migrations.RunPython(dedupe_informes_vigentes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='informeestudiocomplementario',
            name='es_vigente',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='informeestudiocomplementario',
            constraint=models.UniqueConstraint(
                condition=Q(es_vigente=True),
                fields=('estudio',),
                name='uniq_informe_vigente_por_estudio',
            ),
        ),
    ]
