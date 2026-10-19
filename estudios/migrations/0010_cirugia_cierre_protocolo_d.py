# Generated manually for Etapa D — additive only; LIMS untouched.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('turnos', '0010_turno_asistencia_confirmada_en'),
        ('estudios', '0009_sesion_atencion_informe_registro_c'),
    ]

    operations = [
        migrations.AddField(
            model_name='informeestudiocomplementario',
            name='registro_quirurgico',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='informes_estudio_complementario',
                to='turnos.registroquirurgico',
            ),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='cerrado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='estudios_complementarios_cerrados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='fecha_cierre',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='estudiocomplementario',
            name='protocolo_cierre_informe',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='estudios_cerrados_con_esta_version',
                to='estudios.informeestudiocomplementario',
            ),
        ),
        migrations.CreateModel(
            name='HistorialCierreEstudioComplementario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version_protocolo', models.PositiveIntegerField()),
                ('fecha_cierre', models.DateTimeField()),
                ('cerrado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historial_cierres_estudio',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('estudio', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historial_cierres',
                    to='estudios.estudiocomplementario',
                )),
                ('informe', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='historial_cierres',
                    to='estudios.informeestudiocomplementario',
                )),
            ],
            options={
                'verbose_name': 'Historial de cierre de estudio/cirugía',
                'verbose_name_plural': 'Historiales de cierre de estudio/cirugía',
                'ordering': ['-fecha_cierre', '-id'],
            },
        ),
        migrations.CreateModel(
            name='HistorialEntregaEstudioComplementario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version_protocolo', models.PositiveIntegerField()),
                ('fecha_entrega', models.DateTimeField()),
                ('cierre', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='entregas',
                    to='estudios.historialcierreestudiocomplementario',
                )),
                ('entregado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historial_entregas_estudio',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('estudio', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historial_entregas',
                    to='estudios.estudiocomplementario',
                )),
                ('informe', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='historial_entregas',
                    to='estudios.informeestudiocomplementario',
                )),
            ],
            options={
                'verbose_name': 'Historial de entrega de estudio/cirugía',
                'verbose_name_plural': 'Historiales de entrega de estudio/cirugía',
                'ordering': ['-fecha_entrega', '-id'],
            },
        ),
    ]
