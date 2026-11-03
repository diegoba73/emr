from django.db import migrations


CODIGO_SALA = 'sala-extraccion'


def seed_sala_extraccion(apps, schema_editor):
    Puesto = apps.get_model('recepcion', 'PuestoRecepcion')
    Regla = apps.get_model('recepcion', 'ReglaRuteoRecepcion')
    Llegada = apps.get_model('recepcion', 'LlegadaRecepcion')

    sala, _ = Puesto.objects.get_or_create(
        codigo=CODIGO_SALA,
        defaults={
            'nombre': 'Sala de extracción',
            'etiqueta_paciente': 'Sala de extracción',
            'activo': True,
            'modo': 'REGLAS',
            'es_fallback': False,
            'orden': 10,
        },
    )
    # Mantener etiqueta pública aunque el puesto ya existiera.
    changed = False
    if sala.nombre != 'Sala de extracción':
        sala.nombre = 'Sala de extracción'
        changed = True
    if (sala.etiqueta_paciente or '') != 'Sala de extracción':
        sala.etiqueta_paciente = 'Sala de extracción'
        changed = True
    if not sala.activo:
        sala.activo = True
        changed = True
    if sala.modo != 'REGLAS':
        sala.modo = 'REGLAS'
        changed = True
    if changed:
        sala.save()

    # Reglas EXTRACCION viejas (ej. puesto-2) → desactivar y crear/activar la de sala.
    Regla.objects.filter(tipo_actividad='EXTRACCION', activo=True).exclude(
        puesto=sala
    ).update(activo=False)

    regla, created = Regla.objects.get_or_create(
        puesto=sala,
        tipo_actividad='EXTRACCION',
        defaults={
            'nombre': 'Extracciones → Sala de extracción',
            'prioridad': 5,
            'activo': True,
        },
    )
    if not created:
        regla.nombre = 'Extracciones → Sala de extracción'
        regla.prioridad = 5
        regla.activo = True
        regla.save()

    # Reubicar llegadas L abiertas del día (o cualquier EXTRACCION abierta).
    abiertos = (
        'EN_ESPERA_RECEPCION',
        'EN_ESPERA',
        'LLAMADO',
    )
    Llegada.objects.filter(tipo_actividad='EXTRACCION', estado_flujo__in=abiertos).exclude(
        puesto=sala
    ).update(puesto=sala, destino_label='Sala de extracción')


def unseed_sala_extraccion(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('recepcion', '0004_llegada_codigo_llamado'),
    ]

    operations = [
        migrations.RunPython(seed_sala_extraccion, unseed_sala_extraccion),
    ]
