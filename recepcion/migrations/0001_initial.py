import django.db.models.deletion
from django.db import migrations, models


def seed_puestos_y_reglas(apps, schema_editor):
    Puesto = apps.get_model('recepcion', 'PuestoRecepcion')
    Regla = apps.get_model('recepcion', 'ReglaRuteoRecepcion')
    p1, _ = Puesto.objects.get_or_create(
        codigo='puesto-1',
        defaults={
            'nombre': 'Recepción 1',
            'etiqueta_paciente': 'Puesto 1 — Consultas',
            'activo': True,
            'modo': 'REGLAS',
            'es_fallback': True,
            'orden': 1,
        },
    )
    p2, _ = Puesto.objects.get_or_create(
        codigo='puesto-2',
        defaults={
            'nombre': 'Recepción 2',
            'etiqueta_paciente': 'Puesto 2 — Estudios y procedimientos',
            'activo': True,
            'modo': 'REGLAS',
            'es_fallback': False,
            'orden': 2,
        },
    )
    if not Regla.objects.filter(puesto=p1).exists():
        Regla.objects.create(
            puesto=p1,
            nombre='Consultas → Puesto 1',
            prioridad=10,
            activo=True,
            tipo_actividad='CONSULTA',
        )
        Regla.objects.create(
            puesto=p1,
            nombre='Sin turno → Puesto 1',
            prioridad=90,
            activo=True,
            tipo_actividad='SIN_TURNO',
        )
    if not Regla.objects.filter(puesto=p2).exists():
        for tipo, prio, nombre in (
            ('ESTUDIO', 10, 'Estudios → Puesto 2'),
            ('PROCEDIMIENTO', 20, 'Procedimientos → Puesto 2'),
            ('CIRUGIA', 30, 'Cirugías → Puesto 2'),
            ('EXTRACCION', 40, 'Extracciones → Puesto 2'),
        ):
            Regla.objects.create(
                puesto=p2,
                nombre=nombre,
                prioridad=prio,
                activo=True,
                tipo_actividad=tipo,
            )


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('pacientes', '0012_pacienteafiliacion'),
        ('medicos', '0010_medico_email_telefono'),
        ('turnos', '0011_recurso_tipo_extracciones'),
    ]

    operations = [
        migrations.CreateModel(
            name='PuestoRecepcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('codigo', models.SlugField(max_length=32, unique=True)),
                ('nombre', models.CharField(max_length=120)),
                (
                    'etiqueta_paciente',
                    models.CharField(
                        blank=True,
                        help_text='Texto que ve el paciente (ej. Consultas, Estudios). Si vacío, usa nombre.',
                        max_length=120,
                    ),
                ),
                ('activo', models.BooleanField(db_index=True, default=True)),
                (
                    'modo',
                    models.CharField(
                        choices=[('TODO', 'Atiende cualquier llegada'), ('REGLAS', 'Solo lo que matchean sus reglas')],
                        default='REGLAS',
                        max_length=16,
                    ),
                ),
                (
                    'es_fallback',
                    models.BooleanField(
                        default=False,
                        help_text='Si ninguna regla matchea, usar este puesto (solo uno debería serlo).',
                    ),
                ),
                ('orden', models.PositiveSmallIntegerField(default=1)),
            ],
            options={
                'verbose_name': 'Puesto de recepción',
                'verbose_name_plural': 'Puestos de recepción',
                'ordering': ['orden', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ReglaRuteoRecepcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nombre', models.CharField(blank=True, max_length=120)),
                (
                    'prioridad',
                    models.PositiveSmallIntegerField(
                        db_index=True, default=100, help_text='Menor número = se evalúa primero.'
                    ),
                ),
                ('activo', models.BooleanField(db_index=True, default=True)),
                (
                    'tipo_actividad',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('CONSULTA', 'Consulta médica'),
                            ('ESTUDIO', 'Estudio'),
                            ('PROCEDIMIENTO', 'Procedimiento'),
                            ('CIRUGIA', 'Cirugía'),
                            ('EXTRACCION', 'Extracción / lab'),
                            ('SIN_TURNO', 'Sin turno (walk-in)'),
                        ],
                        default='',
                        help_text='Vacío = cualquier tipo de actividad.',
                        max_length=20,
                    ),
                ),
                (
                    'tipo_recurso',
                    models.CharField(
                        blank=True,
                        default='',
                        help_text='Ej. CONSULTORIO, SALA_PROCEDIMIENTO, EXTRACCIONES. Vacío = cualquiera.',
                        max_length=30,
                    ),
                ),
                (
                    'medico',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='reglas_ruteo_recepcion',
                        to='medicos.medico',
                    ),
                ),
                (
                    'puesto',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='reglas',
                        to='recepcion.puestorecepcion',
                    ),
                ),
                (
                    'recurso',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='reglas_ruteo_recepcion',
                        to='turnos.recurso',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Regla de ruteo de recepción',
                'verbose_name_plural': 'Reglas de ruteo de recepción',
                'ordering': ['prioridad', 'id'],
            },
        ),
        migrations.CreateModel(
            name='LlegadaRecepcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'tipo_actividad',
                    models.CharField(
                        choices=[
                            ('CONSULTA', 'Consulta médica'),
                            ('ESTUDIO', 'Estudio'),
                            ('PROCEDIMIENTO', 'Procedimiento'),
                            ('CIRUGIA', 'Cirugía'),
                            ('EXTRACCION', 'Extracción / lab'),
                            ('SIN_TURNO', 'Sin turno'),
                        ],
                        db_index=True,
                        default='SIN_TURNO',
                        max_length=20,
                    ),
                ),
                (
                    'estado_flujo',
                    models.CharField(
                        choices=[
                            ('PROGRAMADO', 'Programado (aún no llegó)'),
                            ('EN_ESPERA_RECEPCION', 'En espera en recepción'),
                            ('EN_ESPERA', 'En espera (destino clínico)'),
                            ('LLAMADO', 'Llamado'),
                            ('EN_ATENCION', 'En atención'),
                            ('ATENDIDO', 'Atendido'),
                            ('NO_ASISTIO', 'No asistió'),
                            ('CANCELADO', 'Cancelado'),
                        ],
                        db_index=True,
                        default='EN_ESPERA_RECEPCION',
                        max_length=24,
                    ),
                ),
                ('fecha', models.DateField(db_index=True)),
                ('checkin_en', models.DateTimeField(blank=True, null=True)),
                ('llamado_en', models.DateTimeField(blank=True, null=True)),
                ('destino_label', models.CharField(blank=True, default='', max_length=120)),
                ('notas', models.CharField(blank=True, default='', max_length=255)),
                ('numero_orden_dia', models.PositiveIntegerField(blank=True, null=True)),
                (
                    'destino_recurso',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='llegadas_destino',
                        to='turnos.recurso',
                    ),
                ),
                (
                    'paciente',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='llegadas_recepcion',
                        to='pacientes.paciente',
                    ),
                ),
                (
                    'puesto',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='llegadas',
                        to='recepcion.puestorecepcion',
                    ),
                ),
                (
                    'turno',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='llegadas_recepcion',
                        to='turnos.turno',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Llegada a recepción',
                'verbose_name_plural': 'Llegadas a recepción',
                'ordering': ['checkin_en', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='llegadarecepcion',
            index=models.Index(fields=['fecha', 'puesto', 'estado_flujo'], name='recepcion_l_fecha_7c8a1a_idx'),
        ),
        migrations.AddIndex(
            model_name='llegadarecepcion',
            index=models.Index(fields=['fecha', 'estado_flujo'], name='recepcion_l_fecha_1f2b3c_idx'),
        ),
        migrations.RunPython(seed_puestos_y_reglas, unseed),
    ]
