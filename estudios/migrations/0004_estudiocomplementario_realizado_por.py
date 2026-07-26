# Generated manually for realizado_por on EstudioComplementario

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('estudios', '0003_estudio_turno_confirmado'),
    ]

    operations = [
        migrations.AddField(
            model_name='estudiocomplementario',
            name='realizado_por',
            field=models.ForeignKey(
                blank=True,
                help_text='Profesional que realizó el estudio; tras VALIDADO solo este usuario (o admin) puede editar.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='estudios_complementarios_realizados',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Realizado / informado por',
            ),
        ),
    ]
