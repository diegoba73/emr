# Generated manually for PaqueteLabContexto + FavoritoLabMedico

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0058_suero_quimica_y_tubo_eritro'),
        ('medicos', '0007_agenda_ambulatoria_20_min'),
        ('movil', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaqueteLabContexto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=40, unique=True)),
                ('nombre', models.CharField(max_length=120)),
                ('contexto', models.CharField(choices=[('GUARDIA', 'Guardia'), ('AMBULATORIO', 'Ambulatorio'), ('INTERNACION', 'Internación')], db_index=True, max_length=20)),
                ('descripcion', models.CharField(blank=True, max_length=255)),
                ('activo', models.BooleanField(default=True)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('examenes', models.ManyToManyField(blank=True, related_name='paquetes_lab_movil', to='laboratorio.tipoexamen')),
                ('paneles', models.ManyToManyField(blank=True, related_name='paquetes_lab_movil', to='laboratorio.panelexamen')),
            ],
            options={
                'verbose_name': 'Paquete lab móvil',
                'verbose_name_plural': 'Paquetes lab móvil',
                'ordering': ['contexto', 'orden', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='FavoritoLabMedico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('medico', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favoritos_lab_movil', to='medicos.medico')),
                ('panel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='favoritos_lab_movil', to='laboratorio.panelexamen')),
                ('tipo_examen', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='favoritos_lab_movil', to='laboratorio.tipoexamen')),
            ],
            options={
                'verbose_name': 'Favorito lab médico',
                'verbose_name_plural': 'Favoritos lab médico',
                'ordering': ['orden', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='favoritolabmedico',
            constraint=models.UniqueConstraint(condition=models.Q(('tipo_examen__isnull', False)), fields=('medico', 'tipo_examen'), name='favorito_lab_medico_examen_uniq'),
        ),
        migrations.AddConstraint(
            model_name='favoritolabmedico',
            constraint=models.UniqueConstraint(condition=models.Q(('panel__isnull', False)), fields=('medico', 'panel'), name='favorito_lab_medico_panel_uniq'),
        ),
    ]
