from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recepcion', '0002_llegadarecepcion_token_publico'),
    ]

    operations = [
        migrations.AddField(
            model_name='puestorecepcion',
            name='ubicacion',
            field=models.CharField(
                blank=True,
                choices=[('CEHTA', 'CEHTA'), ('ICPL', 'ICPL')],
                db_index=True,
                help_text='Sede del puesto. Vacío = visible sin filtro de sede.',
                max_length=10,
                null=True,
            ),
        ),
    ]
