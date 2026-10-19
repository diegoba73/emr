# A3 — SesionActividad + backfill 1:1 idempotente (no sobrescribe sesiones existentes)

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


def forwards_backfill(apps, schema_editor):
    EstudioComplementario = apps.get_model('estudios', 'EstudioComplementario')
    SesionActividad = apps.get_model('estudios', 'SesionActividad')

    def estado_desde(estudio):
        if estudio.estado == 'ANULADO':
            return 'CANCELADA'
        if estudio.estado in ('REALIZADO', 'INFORMADO', 'ENTREGADO'):
            return 'REALIZADA'
        if estudio.turno_id:
            return 'PROGRAMADA'
        return 'PENDIENTE'

    for estudio in EstudioComplementario.objects.all().iterator():
        if SesionActividad.objects.filter(estudio_id=estudio.pk, numero_sesion=1).exists():
            continue
        SesionActividad.objects.create(
            estudio_id=estudio.pk,
            numero_sesion=1,
            turno_id=estudio.turno_id,
            fecha_realizacion=estudio.fecha_realizacion,
            realizado_por_id=estudio.realizado_por_id,
            estado_sesion=estado_desde(estudio),
        )


def backwards_noop(apps, schema_editor):
    # No borrar sesiones en reverse: preserva historia si se revierte parcialmente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('turnos', '0010_turno_asistencia_confirmada_en'),
        ('estudios', '0006_estudio_tipo_actividad_a2'),
    ]

    operations = [
        migrations.CreateModel(
            name='SesionActividad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('numero_sesion', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('fecha_realizacion', models.DateTimeField(blank=True, null=True)),
                ('estado_sesion', models.CharField(
                    choices=[
                        ('PENDIENTE', 'Pendiente'),
                        ('PROGRAMADA', 'Programada'),
                        ('REALIZADA', 'Realizada'),
                        ('CANCELADA', 'Cancelada'),
                    ],
                    db_index=True,
                    default='PENDIENTE',
                    max_length=20,
                )),
                ('estudio', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sesiones',
                    to='estudios.estudiocomplementario',
                )),
                ('realizado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sesiones_actividad_realizadas',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('turno', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sesiones_actividad',
                    to='turnos.turno',
                )),
            ],
            options={
                'verbose_name': 'Sesión de actividad',
                'verbose_name_plural': 'Sesiones de actividad',
                'ordering': ['estudio_id', 'numero_sesion'],
            },
        ),
        migrations.AddConstraint(
            model_name='sesionactividad',
            constraint=models.UniqueConstraint(
                fields=('estudio', 'numero_sesion'),
                name='uniq_sesion_actividad_estudio_numero',
            ),
        ),
        migrations.AddConstraint(
            model_name='sesionactividad',
            constraint=models.UniqueConstraint(
                condition=models.Q(turno__isnull=False),
                fields=('turno',),
                name='uniq_sesion_actividad_turno',
            ),
        ),
        migrations.RunPython(forwards_backfill, backwards_noop),
    ]
