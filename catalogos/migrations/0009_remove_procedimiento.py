from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogos', '0008_backfill_pueblo_de_luis'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Procedimiento',
        ),
        migrations.AlterModelOptions(
            name='procedimientocatalogo',
            options={
                'ordering': ['nombre'],
                'verbose_name': 'Procedimiento',
                'verbose_name_plural': 'Procedimientos',
            },
        ),
    ]
