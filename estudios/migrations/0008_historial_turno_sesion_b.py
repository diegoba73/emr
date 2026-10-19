# B — HistorialTurnoSesionActividad (trazabilidad reprogramación; sin campos en Turno)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('turnos', '0010_turno_asistencia_confirmada_en'),
        ('estudios', '0007_sesion_actividad_a3'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialTurnoSesionActividad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('motivo', models.TextField()),
                ('actor', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historial_turnos_sesion_actividad',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('sesion', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='historial_turnos',
                    to='estudios.sesionactividad',
                )),
                ('turno_anterior', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='+',
                    to='turnos.turno',
                )),
                ('turno_nuevo', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='+',
                    to='turnos.turno',
                )),
            ],
            options={
                'verbose_name': 'Historial de turno de sesión',
                'verbose_name_plural': 'Historiales de turno de sesión',
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
