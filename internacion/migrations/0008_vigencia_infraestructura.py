from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('internacion', '0007_ingreso_hc_fase0')]
    operations = [
        migrations.AddField(model_name='sector', name='activo',
                            field=models.BooleanField(default=True, verbose_name='En uso')),
        migrations.AddField(model_name='cama', name='activo',
                            field=models.BooleanField(default=True, verbose_name='En uso')),
        migrations.AlterField(model_name='cama', name='sector',
            field=models.ForeignKey(to='internacion.sector', on_delete=models.PROTECT,
                                    related_name='camas', verbose_name='Sector')),
        migrations.AlterField(model_name='internacion', name='cama',
            field=models.ForeignKey(to='internacion.cama', on_delete=models.PROTECT,
                                    related_name='internaciones', verbose_name='Cama')),
    ]
