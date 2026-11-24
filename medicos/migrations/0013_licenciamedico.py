from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medicos', '0012_feriado'),
    ]

    operations = [
        migrations.CreateModel(
            name='LicenciaMedico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField(verbose_name='Fecha inicio')),
                ('fecha_fin', models.DateField(verbose_name='Fecha fin')),
                ('motivo', models.CharField(
                    choices=[
                        ('LICENCIA_MEDICA', 'Licencia médica'),
                        ('CONGRESO', 'Congreso'),
                        ('ESTUDIO', 'Estudio'),
                        ('PERSONAL', 'Asuntos personales'),
                        ('OTRO', 'Otro'),
                    ],
                    max_length=30,
                    verbose_name='Motivo',
                )),
                ('detalle', models.CharField(
                    blank=True,
                    help_text='Opcional (p. ej. nombre del congreso).',
                    max_length=200,
                    verbose_name='Detalle',
                )),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('medico', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='licencias',
                    to='medicos.medico',
                    verbose_name='Médico / profesional',
                )),
            ],
            options={
                'verbose_name': 'Licencia de médico',
                'verbose_name_plural': 'Licencias de médicos',
                'ordering': ['-fecha_inicio', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='licenciamedico',
            index=models.Index(
                fields=['medico', 'fecha_inicio', 'fecha_fin'],
                name='medicos_lic_medico__a1b2c3_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='licenciamedico',
            index=models.Index(
                fields=['activo', 'fecha_inicio', 'fecha_fin'],
                name='medicos_lic_activo__d4e5f6_idx',
            ),
        ),
    ]
