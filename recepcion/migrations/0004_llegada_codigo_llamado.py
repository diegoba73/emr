from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recepcion', '0003_puestorecepcion_ubicacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='llegadarecepcion',
            name='prefijo_llamado',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='T/S/E/P/L según motivo de anuncio.',
                max_length=1,
            ),
        ),
        migrations.AddField(
            model_name='llegadarecepcion',
            name='codigo_llamado',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Código público tipo T03, L01.',
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name='llegadarecepcion',
            name='zona_llamado',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='RECEPCION o MEDICO: en qué mitad de la TV se muestra el llamado.',
                max_length=12,
            ),
        ),
    ]
