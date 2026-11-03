from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recepcion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='llegadarecepcion',
            name='token_publico',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Token opaco para página de espera del paciente (QR).',
                max_length=48,
                null=True,
                unique=True,
            ),
        ),
    ]
