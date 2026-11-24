"""Disponibilidad compartida por calendario, reservas y reprogramaciones."""
from datetime import datetime, time, timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import DisponibilidadMedico, ExcepcionMedico, Feriado, LicenciaMedico, Medico

DEFAULT_DURACION_MIN = 20
# Compat: importadores legacy. Preferir duracion_de(medico).
DURACION = timedelta(minutes=DEFAULT_DURACION_MIN)

ESTADOS_TURNO_PENDIENTE_FERIADO = ('RESERVADO', 'CONFIRMADO')


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


def feriado_activo(fecha):
    """Devuelve el Feriado activo de la fecha, o None."""
    return Feriado.objects.filter(fecha=fecha, activo=True).first()


def mensaje_feriado(fecha) -> str:
    feriado = feriado_activo(fecha)
    if not feriado:
        return ''
    return f'Día feriado: {feriado.nombre}.'


def licencia_activa(medico, fecha):
    """Devuelve una LicenciaMedico activa que cubra la fecha para ese médico, o None."""
    if not medico or not fecha:
        return None
    medico_id = getattr(medico, 'pk', medico)
    return (
        LicenciaMedico.objects.filter(
            medico_id=medico_id,
            activo=True,
            fecha_inicio__lte=fecha,
            fecha_fin__gte=fecha,
        )
        .order_by('fecha_inicio', 'id')
        .first()
    )


def mensaje_licencia(medico, fecha) -> str:
    licencia = licencia_activa(medico, fecha)
    if not licencia:
        return ''
    motivo = licencia.get_motivo_display()
    detalle = (licencia.detalle or '').strip()
    extra = f' ({detalle})' if detalle else ''
    return f'El profesional está de licencia: {motivo}{extra}.'


def turnos_pendientes_feriado(fecha):
    """Turnos RESERVADO/CONFIRMADO del día local que secretaría debe gestionar."""
    from turnos.models import Turno

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(fecha, time.min), tz)
    fin = inicio + timedelta(days=1)
    return (
        Turno.objects.filter(
            fecha_hora_inicio__gte=inicio,
            fecha_hora_inicio__lt=fin,
            estado__in=ESTADOS_TURNO_PENDIENTE_FERIADO,
        )
        .select_related('paciente', 'medico')
        .order_by('fecha_hora_inicio')
    )


def turnos_pendientes_licencia(licencia: LicenciaMedico):
    """Turnos RESERVADO/CONFIRMADO del médico en el rango de la licencia."""
    from turnos.models import Turno

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(licencia.fecha_inicio, time.min), tz)
    fin = timezone.make_aware(
        datetime.combine(licencia.fecha_fin + timedelta(days=1), time.min),
        tz,
    )
    return (
        Turno.objects.filter(
            medico_id=licencia.medico_id,
            fecha_hora_inicio__gte=inicio,
            fecha_hora_inicio__lt=fin,
            estado__in=ESTADOS_TURNO_PENDIENTE_FERIADO,
        )
        .select_related('paciente', 'medico')
        .order_by('fecha_hora_inicio')
    )


def _serializar_turno_pendiente(t) -> dict:
    paciente = t.paciente
    medico = t.medico
    return {
        'id': t.pk,
        'estado': t.estado,
        'fecha_hora_inicio': t.fecha_hora_inicio.isoformat() if t.fecha_hora_inicio else None,
        'paciente_id': paciente.pk if paciente else None,
        'paciente_nombre': (
            f'{paciente.apellido}, {paciente.nombre}'.strip(', ') if paciente else None
        ),
        'medico_id': medico.pk if medico else None,
        'medico_nombre': (
            f'{medico.apellido}, {medico.nombre}'.strip(', ') if medico else None
        ),
    }


def serializar_turnos_pendientes_feriado(fecha):
    return [_serializar_turno_pendiente(t) for t in turnos_pendientes_feriado(fecha)]


def serializar_turnos_pendientes_licencia(licencia: LicenciaMedico):
    return [_serializar_turno_pendiente(t) for t in turnos_pendientes_licencia(licencia)]


def intervalos(medico, fecha, tipo=None):
    if feriado_activo(fecha):
        return
    if licencia_activa(medico, fecha):
        return
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


def slots_disponibles(medico, fecha, tipo=None, recurso_ids=None):
    """Slots libres. Si ``recurso_ids`` es un set/lista, solo esas salas/consultorios."""
    permitidos = set(recurso_ids) if recurso_ids is not None else None
    vistos = set()
    minutes = duracion_minutos(medico)
    for horario, inicio, fin in intervalos(medico, fecha, tipo):
        # Sin consultorio/sala en la franja no se ofrece el slot (evita alta incorrecta).
        if not horario.recurso_id:
            continue
        if permitidos is not None and horario.recurso_id not in permitidos:
            continue
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


def franja_publicada(medico, inicio, fin, *, tipo=None, horario_id=None):
    """Devuelve la DisponibilidadMedico que cubre exactamente [inicio, fin], o None."""
    if not medico or not inicio or not fin:
        return None
    if timezone.is_naive(inicio):
        inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
    if timezone.is_naive(fin):
        fin = timezone.make_aware(fin, timezone.get_current_timezone())
    local = timezone.localtime(inicio)
    msg = mensaje_feriado(local.date())
    if msg:
        raise ValidationError(msg)
    msg_lic = mensaje_licencia(medico, local.date())
    if msg_lic:
        raise ValidationError(msg_lic)
    for horario, a, b in intervalos(medico, local.date(), tipo):
        if a == inicio and b == fin and (horario_id is None or horario.pk == horario_id):
            return horario
    return None


def recurso_de_franja_publicada(
    medico,
    inicio,
    fin,
    *,
    tipo=None,
    horario_id=None,
    recurso_solicitado=None,
):
    """
    Recurso obligatorio de la franja publicada del médico.

    Evita que secretaría elija un consultorio/sala distinto al de la agenda.
    """
    horario = franja_publicada(medico, inicio, fin, tipo=tipo, horario_id=horario_id)
    if horario is None:
        raise ValidationError('El horario no está disponible en la agenda del médico.')
    if not horario.recurso_id:
        raise ValidationError(
            'La franja del médico no tiene consultorio/sala asignado. '
            'Configurá el recurso en Horarios de atención.'
        )
    if recurso_solicitado is not None and recurso_solicitado.pk != horario.recurso_id:
        raise ValidationError(
            'El consultorio/sala debe ser el asignado en la agenda del médico para ese horario.'
        )
    return horario.recurso


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


def validar_reserva(
    medico,
    inicio,
    fin,
    recurso=None,
    *,
    excluir=None,
    exigir_horario=False,
    horario_id=None,
    permitir_sobreturno=False,
):
    if inicio and timezone.is_naive(inicio):
        inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
    if fin is not None and timezone.is_naive(fin):
        fin = timezone.make_aware(fin, timezone.get_current_timezone())
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
    local = timezone.localtime(inicio)
    msg_feriado = mensaje_feriado(local.date())
    if msg_feriado:
        raise ValidationError(msg_feriado)
    msg_lic = mensaje_licencia(medico, local.date())
    if msg_lic:
        raise ValidationError(msg_lic)
    recurso_efectivo = recurso
    if exigir_horario or configurado:
        if inicio <= timezone.now():
            raise ValidationError('Seleccione un horario futuro.')
        tipo = tipo_para_recurso(recurso) if recurso is not None else None
        encontrados = [
            h for h, a, b in intervalos(medico, local.date(), tipo)
            if a == inicio and b == fin and (horario_id is None or h.pk == horario_id)
        ]
        if not encontrados:
            raise ValidationError('El horario no está disponible en la agenda del médico.')
        horario = encontrados[0]
        if not horario.recurso_id:
            raise ValidationError(
                'La franja del médico no tiene consultorio/sala asignado. '
                'Configurá el recurso en Horarios de atención.'
            )
        if recurso is not None and recurso.pk != horario.recurso_id:
            raise ValidationError(
                'El consultorio/sala debe ser el asignado en la agenda del médico para ese horario.'
            )
        recurso_efectivo = horario.recurso
        if recurso_efectivo:
            Recurso.objects.select_for_update().get(pk=recurso_efectivo.pk)
    # Sobreturno (secretaría): permite un turno extra sobre un slot ya ocupado.
    if permitir_sobreturno:
        return
    if ocupado(medico, inicio, fin, recurso_efectivo, excluir):
        raise ValidationError('El horario ya está ocupado. Seleccione otro.')
