"""Disponibilidad compartida por calendario, reservas y reprogramaciones."""
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import DisponibilidadMedico, ExcepcionMedico, Medico

DEFAULT_DURACION_MIN = 20
# Compat: importadores legacy. Preferir duracion_de(medico).
DURACION = timedelta(minutes=DEFAULT_DURACION_MIN)


def duracion_minutos(medico) -> int:
    if medico is None:
        return DEFAULT_DURACION_MIN
    minutes = getattr(medico, 'duracion_slot_min', None) or DEFAULT_DURACION_MIN
    if minutes not in Medico.DURACIONES_SLOT_PERMITIDAS:
        return DEFAULT_DURACION_MIN
    return minutes


def duracion_de(medico) -> timedelta:
    return timedelta(minutes=duracion_minutos(medico))


def tipo_para_recurso(recurso):
    return 'ESTUDIO' if recurso and recurso.tipo_recurso in ('SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA') else 'CONSULTA'


def intervalos(medico, fecha, tipo=None):
    horarios = DisponibilidadMedico.objects.filter(medico=medico, activo=True, dia_semana=fecha.weekday()).select_related('recurso')
    if tipo:
        horarios = horarios.filter(tipo=tipo)
    excepciones = list(ExcepcionMedico.objects.filter(medico=medico, fecha=fecha))
    tz = timezone.get_current_timezone()
    slot = duracion_de(medico)
    def dt(hora):
        return timezone.make_aware(datetime.combine(fecha, hora), tz)
    for horario in horarios:
        if horario.recurso and not horario.recurso.activo:
            continue
        inicio, fin = dt(horario.hora_inicio), dt(horario.hora_fin)
        ajustes = [e for e in excepciones if e.tipo == 'AJUSTE' and e.hora_inicio and e.hora_fin]
        rangos = [(dt(e.hora_inicio), dt(e.hora_fin)) for e in ajustes] if ajustes else [(inicio, fin)]
        for inicio, fin in rangos:
            while inicio + slot <= fin:
                final = inicio + slot
                bloqueado = any(e.tipo == 'BLOQUEO' and (
                    not e.hora_inicio or not e.hora_fin or
                    inicio < dt(e.hora_fin) and final > dt(e.hora_inicio)
                ) for e in excepciones)
                if not bloqueado:
                    yield horario, inicio, final
                inicio = final


def ocupado(medico, inicio, fin, recurso=None, excluir=None):
    from turnos.models import Turno
    from django.db.models import Q
    qs = Turno.objects.exclude(estado__in=['CANCELADO', 'DISPONIBLE'])
    if excluir:
        qs = qs.exclude(pk=excluir)
    alcance = Q(medico=medico) if medico else Q(pk__in=[])
    if recurso:
        alcance |= Q(recurso=recurso)
    slot = duracion_de(medico)
    # Incluir turnos iniciados antes del día y legacy sin fin.
    qs = qs.filter(alcance, fecha_hora_inicio__lt=fin).filter(
        Q(fecha_hora_fin__gt=inicio) |
        Q(fecha_hora_fin__isnull=True, fecha_hora_inicio__gt=inicio-slot)
    )
    return qs.exists()


def slots_disponibles(medico, fecha, tipo=None):
    vistos = set()
    minutes = duracion_minutos(medico)
    for horario, inicio, fin in intervalos(medico, fecha, tipo):
        key = (inicio, horario.tipo)
        if inicio <= timezone.now() or key in vistos or ocupado(medico, inicio, fin, horario.recurso):
            continue
        vistos.add(key)
        yield {
            'horario_id': horario.pk,
            'inicio': inicio.isoformat(),
            'fin': fin.isoformat(),
            'duracion_min': minutes,
            'tipo': horario.tipo,
            'recurso_id': horario.recurso_id,
            'recurso_nombre': horario.recurso.nombre if horario.recurso_id else None,
        }


def dias_disponibles(medico, desde, hasta, tipo=None):
    """Días con al menos un slot libre entre desde y hasta (inclusive)."""
    if hasta < desde:
        return []
    if (hasta - desde).days > 62:
        raise ValidationError('El rango máximo es de 62 días.')
    dias_semana = set(
        DisponibilidadMedico.objects.filter(medico=medico, activo=True)
        .filter(**({'tipo': tipo} if tipo else {}))
        .values_list('dia_semana', flat=True)
        .distinct()
    )
    if not dias_semana:
        return []
    resultado = []
    dia = desde
    while dia <= hasta:
        if dia.weekday() in dias_semana:
            cantidad = sum(1 for _ in slots_disponibles(medico, dia, tipo))
            if cantidad:
                resultado.append({'fecha': dia.isoformat(), 'cantidad_slots': cantidad})
        dia += timedelta(days=1)
    return resultado


def validar_reserva(medico, inicio, fin, recurso=None, *, excluir=None, exigir_horario=False, horario_id=None):
    slot = duracion_de(medico)
    minutes = duracion_minutos(medico)
    if inicio and fin != inicio + slot:
        raise ValidationError({'fecha_hora_fin': f'Los turnos de este médico deben durar {minutes} minutos.'})
    if exigir_horario and (not medico or not inicio):
        raise ValidationError('Seleccione un médico y un horario disponible.')
    if not inicio:
        return
    # El médico funciona como cerrojo común para altas y reprogramaciones.
    if medico:
        Medico.objects.select_for_update().get(pk=medico.pk)
    from turnos.models import Recurso
    if recurso:
        Recurso.objects.select_for_update().get(pk=recurso.pk)
    configurado = medico and DisponibilidadMedico.objects.filter(medico=medico).exists()
    if exigir_horario or configurado:
        local = timezone.localtime(inicio)
        if inicio <= timezone.now():
            raise ValidationError('Seleccione un horario futuro.')
        encontrados = [h for h, a, b in intervalos(medico, local.date(), tipo_para_recurso(recurso))
                       if a == inicio and b == fin and (horario_id is None or h.pk == horario_id)
                       and (h.recurso_id is None or h.recurso_id == getattr(recurso, 'pk', None))]
        if not encontrados:
            raise ValidationError('El horario no está disponible en la agenda del médico.')
    if ocupado(medico, inicio, fin, recurso, excluir):
        raise ValidationError('El horario ya está ocupado. Seleccione otro.')
