from django.db import migrations, models

import estudios.practicas_cehta


class Migration(migrations.Migration):

    dependencies = [
        ('estudios', '0004_estudiocomplementario_realizado_por'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tipoestudiocomplementario',
            old_name='modalidad',
            new_name='practica',
        ),
        migrations.RenameField(
            model_name='estudiocomplementario',
            old_name='modalidad',
            new_name='practica',
        ),
        migrations.AlterField(
            model_name='tipoestudiocomplementario',
            name='practica',
            field=models.CharField(
                max_length=80,
                choices=estudios.practicas_cehta.PRACTICA_CHOICES,
            ),
        ),
        migrations.AlterField(
            model_name='estudiocomplementario',
            name='practica',
            field=models.CharField(
                max_length=80,
                choices=estudios.practicas_cehta.PRACTICA_CHOICES,
            ),
        ),
    ]
