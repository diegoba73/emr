"""Disponibilidad para asignar/agendar/reprogramar estudios (B).

Duración variable (inicio/fin); no altera la semántica de consultorio
(`medicos.agenda.validar_reserva` queda intacta para agenda general).
"""
from __future__ import annotations

from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from medicos.agenda import ocupado, tipo_para_recurso
from medicos.models import DisponibilidadMedico, ExcepcionMedico, Medico
from turnos.models import Recurso
from turnos.validacion_sala import validar_disponibilidad_sala_estudio


def _cubre_intervalo(medico, inicio, fin, recurso=None) -> bool:
    """True si [inicio, fin] cae dentro de horarios activos y fuera de bloqueos."""
    local = timezone.localtime(inicio)
    fecha = local.date()
    if timezone.localtime(fin).date() != fecha:
        return False

    horarios = DisponibilidadMedico.objects.filter(
        medico=medico, activo=True, dia_semana=fecha.weekday()
    ).select_related('recurso')
    tipo = tipo_para_recurso(recurso)
    if tipo:
        horarios = horarios.filter(tipo=tipo)

    excepciones = list(ExcepcionMedico.objects.filter(medico=medico, fecha=fecha))
    tz = timezone.get_current_timezone()

    def dt(hora):
        return timezone.make_aware(datetime.combine(fecha, hora), tz)

    for e in excepciones:
        if e.tipo != 'BLOQUEO':
            continue
        if not e.hora_inicio or not e.hora_fin:
            return False
        if inicio < dt(e.hora_fin) and fin > dt(e.hora_inicio):
            return False

    for horario in horarios:
        if horario.recurso_id and not horario.recurso.activo:
            continue
        if recurso and horario.recurso_id and horario.recurso_id != recurso.pk:
            continue
        base_inicio, base_fin = dt(horario.hora_inicio), dt(horario.hora_fin)
        ajustes = [
            e for e in excepciones
            if e.tipo == 'AJUSTE' and e.hora_inicio and e.hora_fin
        ]
        rangos = (
            [(dt(e.hora_inicio), dt(e.hora_fin)) for e in ajustes]
            if ajustes
            else [(base_inicio, base_fin)]
        )
        if any(a <= inicio and fin <= b for a, b in rangos):
            return True
    return False


def _lock_recursos_profesionales(*, medico=None, recurso=None):
    """Orden estable por PK (médico luego recurso) para evitar deadlocks."""
    if medico is not None:
        Medico.objects.select_for_update().get(pk=medico.pk)
    if recurso is not None:
        Recurso.objects.select_for_update().get(pk=recurso.pk)


def validar_disponibilidad_reserva_estudio(
    *,
    medico,
    recurso,
    fecha_hora_inicio,
    fecha_hora_fin,
    excluir_turno_id: int | None = None,
) -> None:
    """Validación completa para flujo estudios (sin duración fija de consultorio)."""
    if not fecha_hora_inicio or not fecha_hora_fin:
        raise ValidationError('Indique fecha/hora de inicio y fin.')
    if fecha_hora_fin <= fecha_hora_inicio:
        raise ValidationError(
            {'fecha_hora_fin': 'La fecha/hora de fin debe ser posterior al inicio.'}
        )

    _lock_recursos_profesionales(medico=medico, recurso=recurso)

    if medico and DisponibilidadMedico.objects.filter(medico=medico).exists():
        if fecha_hora_inicio <= timezone.now():
            raise ValidationError('Seleccione un horario futuro.')
        if not _cubre_intervalo(medico, fecha_hora_inicio, fecha_hora_fin, recurso):
            raise ValidationError('El horario no está disponible en la agenda del médico.')

    if ocupado(medico, fecha_hora_inicio, fecha_hora_fin, recurso, excluir_turno_id):
        raise ValidationError('El horario ya está ocupado. Seleccione otro.')

    validar_disponibilidad_sala_estudio(
        recurso=recurso,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        excluir_turno_id=excluir_turno_id,
    )
