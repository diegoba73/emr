# Cobertura dinámica: modelo nuevo + etiquetas neutrales + desactivar reglas tipo→puesto (salvo L).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_cobertura_dinamica(apps, schema_editor):
    Puesto = apps.get_model('recepcion', 'PuestoRecepcion')
    Regla = apps.get_model('recepcion', 'ReglaRuteoRecepcion')

    neutrales = {
        'puesto-1': ('Puesto 1', 'Puesto 1'),
        'puesto-2': ('Puesto 2', 'Puesto 2'),
    }
    for codigo, (nombre, etiqueta) in neutrales.items():
        p = Puesto.objects.filter(codigo=codigo).first()
        if not p:
            continue
        changed = False
        if p.nombre != nombre:
            p.nombre = nombre
            changed = True
        if (p.etiqueta_paciente or '') != etiqueta:
            p.etiqueta_paciente = etiqueta
            changed = True
        # Geografía: atienden según cobertura del día, no modo REGLAS fijo.
        if p.modo != 'TODO':
            p.modo = 'TODO'
            changed = True
        if changed:
            p.save()

    # Desactivar reglas secretaría (tipo→puesto). Mantener EXTRACCION → sala.
    Regla.objects.filter(activo=True).exclude(tipo_actividad='EXTRACCION').update(activo=False)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recepcion', '0005_sala_extraccion'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoberturaRecepcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('fecha', models.DateField(db_index=True)),
                (
                    'tipos',
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='Lista de tipo_actividad que atiende hoy (CONSULTA, SIN_TURNO, …).',
                    ),
                ),
                (
                    'sede',
                    models.CharField(
                        blank=True,
                        choices=[('CEHTA', 'CEHTA'), ('ICPL', 'ICPL')],
                        db_index=True,
                        help_text='Sede opcional. Vacío = aplica sin filtro de sede.',
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    'puesto',
                    models.ForeignKey(
                        help_text='Ventanilla física donde está hoy (Puesto 1 / 2).',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='coberturas',
                        to='recepcion.puestorecepcion',
                    ),
                ),
                (
                    'usuario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='coberturas_recepcion',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Cobertura de recepción',
                'verbose_name_plural': 'Coberturas de recepción',
                'ordering': ['-fecha', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='coberturarecepcion',
            constraint=models.UniqueConstraint(
                fields=('usuario', 'fecha'),
                name='recepcion_cobertura_user_fecha_uniq',
            ),
        ),
        migrations.AlterModelOptions(
            name='reglaruteorecepcion',
            options={
                'ordering': ['prioridad', 'id'],
                'verbose_name': 'Regla de ruteo de recepción',
                'verbose_name_plural': 'Reglas de ruteo de recepción',
            },
        ),
        migrations.RunPython(seed_cobertura_dinamica, noop_reverse),
    ]
