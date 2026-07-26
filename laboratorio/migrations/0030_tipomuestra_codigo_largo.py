from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0029_laboratorio_derivacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tipomuestra",
            name="codigo",
            field=models.CharField(max_length=64, unique=True, verbose_name="Código"),
        ),
        migrations.AlterField(
            model_name="tipomuestra",
            name="nombre",
            field=models.CharField(max_length=200, verbose_name="Nombre"),
        ),
    ]