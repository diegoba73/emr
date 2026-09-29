"""Disponibilidad compartida por calendario, reservas y reprogramaciones."""
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import DisponibilidadMedico, ExcepcionMedico, Medico

DURACION = timedelta(minutes=20)


def tipo_para_recurso(recurso):
    return 'ESTUDIO' if recurso and recurso.tipo_recurso in ('SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA') else 'CONSULTA'


def intervalos(medico, fecha, tipo=None):
    horarios = DisponibilidadMedico.objects.filter(medico=medico, activo=True, dia_semana=fecha.weekday()).select_related('recurso')
    if tipo:
        horarios = horarios.filter(tipo=tipo)
    excepciones = list(ExcepcionMedico.objects.filter(medico=medico, fecha=fecha))
    tz = timezone.get_current_timezone()
    def dt(hora):
        return timezone.make_aware(datetime.combine(fecha, hora), tz)
    for horario in horarios:
        if horario.recurso and not horario.recurso.activo:
            continue
        inicio, fin = dt(horario.hora_inicio), dt(horario.hora_fin)
        ajustes = [e for e in excepciones if e.tipo == 'AJUSTE' and e.hora_inicio and e.hora_fin]
        rangos = [(dt(e.hora_inicio), dt(e.hora_fin)) for e in ajustes] if ajustes else [(inicio, fin)]
        for inicio, fin in rangos:
            while inicio + DURACION <= fin:
                final = inicio + DURACION
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
    # Incluir turnos iniciados antes del día y legacy sin fin.
    qs = qs.filter(alcance, fecha_hora_inicio__lt=fin).filter(
        Q(fecha_hora_fin__gt=inicio) |
        Q(fecha_hora_fin__isnull=True, fecha_hora_inicio__gt=inicio-DURACION)
    )
    return qs.exists()


def slots_disponibles(medico, fecha, tipo=None):
    vistos = set()
    for horario, inicio, fin in intervalos(medico, fecha, tipo):
        key = (inicio, horario.tipo)
        if inicio <= timezone.now() or key in vistos or ocupado(medico, inicio, fin, horario.recurso):
            continue
        vistos.add(key)
        yield {'horario_id': horario.pk, 'inicio': inicio.isoformat(), 'fin': fin.isoformat(),
               'duracion_min': 20, 'tipo': horario.tipo}


def validar_reserva(medico, inicio, fin, recurso=None, *, excluir=None, exigir_horario=False, horario_id=None):
    if inicio and fin != inicio + DURACION:
        raise ValidationError({'fecha_hora_fin': 'Los turnos deben durar 20 minutos.'})
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
