from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0009_medico_duracion_slot_min'),
    ]

    operations = [
        migrations.AddField(
            model_name='medico',
            name='email',
            field=models.EmailField(blank=True, null=True, verbose_name='Email'),
        ),
        migrations.AddField(
            model_name='medico',
            name='telefono',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Teléfono'),
        ),
    ]
