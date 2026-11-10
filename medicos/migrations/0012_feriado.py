from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0011_medico_sedes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Feriado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(unique=True)),
                ('nombre', models.CharField(max_length=200)),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Feriado',
                'verbose_name_plural': 'Feriados',
                'ordering': ['-fecha'],
            },
        ),
    ]
