"""Catálogo ObraSocial + backfill desde texto libre + swap a FK."""

import re

from django.db import migrations, models
import django.db.models.deletion


SEED = (
    ('PARTICULAR', 'Particular'),
    ('OSDE', 'OSDE'),
    ('PAMI', 'PAMI'),
    ('SEROS', 'SEROS'),
    ('SWISS_MEDICAL', 'Swiss Medical'),
    ('GALENO', 'Galeno'),
    ('MEDICUS', 'Medicus'),
    ('IOMA', 'IOMA'),
    ('OSECAC', 'OSECAC'),
)


def _norm(value):
    return (str(value) if value is not None else '').strip().upper()


def _codigo_legacy(text):
    raw = _norm(text)
    code = re.sub(r'[^A-Z0-9]+', '_', raw).strip('_')[:80]
    return code or 'LEGACY'


def seed_and_backfill(apps, schema_editor):
    ObraSocial = apps.get_model('pacientes', 'ObraSocial')
    Paciente = apps.get_model('pacientes', 'Paciente')
    PacienteAfiliacion = apps.get_model('pacientes', 'PacienteAfiliacion')

    for codigo, nombre in SEED:
        ObraSocial.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'activo': True},
        )

    def resolve(text, *, require=False):
        t = _norm(text)
        if not t:
            if require:
                obj, _ = ObraSocial.objects.get_or_create(
                    codigo='PARTICULAR',
                    defaults={'nombre': 'Particular', 'activo': True},
                )
                return obj
            return None
        found = (
            ObraSocial.objects.filter(codigo=t).first()
            or ObraSocial.objects.filter(nombre__iexact=t).first()
        )
        if found:
            return found
        codigo = _codigo_legacy(t)
        base = codigo
        n = 2
        while ObraSocial.objects.filter(codigo=codigo).exists():
            codigo = f'{base}_{n}'[:80]
            n += 1
        return ObraSocial.objects.create(codigo=codigo, nombre=t, activo=True)

    for pac in Paciente.objects.all().iterator():
        raw = getattr(pac, 'obra_social_old', None)
        os_obj = resolve(raw, require=False)
        pac.obra_social_id = os_obj.pk if os_obj else None
        pac.save(update_fields=['obra_social_id'])

    for afil in PacienteAfiliacion.objects.all().iterator():
        raw = getattr(afil, 'obra_social_old', None)
        os_obj = resolve(raw, require=True)
        afil.obra_social_id = os_obj.pk
        afil.save(update_fields=['obra_social_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pacientes', '0013_problema_clinico_y_dx_orden'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObraSocial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=80, unique=True, verbose_name='Código')),
                ('nombre', models.CharField(max_length=150, verbose_name='Nombre')),
                ('activo', models.BooleanField(db_index=True, default=True, verbose_name='Activo')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Obra social',
                'verbose_name_plural': 'Obras sociales',
                'ordering': ['nombre', 'codigo'],
            },
        ),
        # Renombrar CharField viejos para convivir con la FK temporal.
        migrations.RenameField(
            model_name='paciente',
            old_name='obra_social',
            new_name='obra_social_old',
        ),
        migrations.RenameField(
            model_name='pacienteafiliacion',
            old_name='obra_social',
            new_name='obra_social_old',
        ),
        migrations.AddField(
            model_name='paciente',
            name='obra_social',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pacientes',
                to='pacientes.obrasocial',
                verbose_name='Obra Social',
            ),
        ),
        migrations.AddField(
            model_name='pacienteafiliacion',
            name='obra_social',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='afiliaciones',
                to='pacientes.obrasocial',
                verbose_name='Obra Social',
            ),
        ),
        migrations.RunPython(seed_and_backfill, noop_reverse),
        migrations.AlterField(
            model_name='pacienteafiliacion',
            name='obra_social',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='afiliaciones',
                to='pacientes.obrasocial',
                verbose_name='Obra Social',
            ),
        ),
        migrations.RemoveField(
            model_name='paciente',
            name='obra_social_old',
        ),
        migrations.RemoveField(
            model_name='pacienteafiliacion',
            name='obra_social_old',
        ),
        migrations.AlterModelOptions(
            name='pacienteafiliacion',
            options={
                'ordering': ['-es_principal', 'obra_social__nombre', 'id'],
                'verbose_name': 'Afiliación de paciente',
                'verbose_name_plural': 'Afiliaciones de paciente',
            },
        ),
    ]
