from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0007_agenda_ambulatoria_20_min'),
    ]

    operations = [
        migrations.AddField(
            model_name='medico',
            name='ambito_atencion',
            field=models.CharField(
                choices=[
                    ('COMPLETO', 'Completo (ambulatorio, guardia e internación)'),
                    ('AMBULATORIO', 'Solo ambulatorio'),
                ],
                db_index=True,
                default='COMPLETO',
                help_text='COMPLETO ve guardia e internación; AMBULATORIO solo consultorio.',
                max_length=20,
                verbose_name='Ámbito de atención',
            ),
        ),
    ]
