from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pacientes', '0010_paciente_creado_modificado_por'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='estado_civil',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='Estado civil'),
        ),
        migrations.AddField(
            model_name='paciente',
            name='familiar_nombre',
            field=models.CharField(
                blank=True,
                default='',
                max_length=150,
                verbose_name='Familiar (nombre y apellido)',
            ),
        ),
        migrations.AddField(
            model_name='paciente',
            name='familiar_telefono',
            field=models.CharField(
                blank=True,
                default='',
                max_length=30,
                verbose_name='Teléfono del familiar',
            ),
        ),
    ]
