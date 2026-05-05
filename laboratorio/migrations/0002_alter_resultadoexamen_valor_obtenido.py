# Permitir valor pendiente en ResultadoExamen (flujo cargar-resultados)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resultadoexamen',
            name='valor_obtenido',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Puede ser número o texto (ej: 'Positivo', 'Negativo', '120.5'). Vacío hasta cargar resultado.",
                max_length=255,
                verbose_name='Valor Obtenido',
            ),
        ),
    ]
