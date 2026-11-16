import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('turnos', '0013_turno_es_sobreturno'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialReprogramacionTurno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('motivo', models.TextField()),
                ('actor', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historial_reprogramaciones_turno',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('turno_anterior', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='reprogramaciones_como_anterior',
                    to='turnos.turno',
                )),
                ('turno_nuevo', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='reprogramaciones_como_nuevo',
                    to='turnos.turno',
                )),
            ],
            options={
                'verbose_name': 'Historial de reprogramación de turno',
                'verbose_name_plural': 'Historiales de reprogramación de turno',
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
