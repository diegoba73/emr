"""Recordatorios con registro persistente, reintentos y recibos del proveedor.

ACEPTADO/ENTREGADO no significan que el usuario haya leído la notificación.

Tipos:
- CONFIRMAR_TURNO: turnos RESERVADO a más de 1 día (paciente debe confirmar estado).
- ASISTENCIA: turnos CONFIRMADO en ventana ~24 hs (¿venís?).
"""
from datetime import datetime, time as dtime, timedelta
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from turnos.models import Turno
from .models import DispositivoPush, RecordatorioTurno

EXPO_SEND = 'https://exp.host/--/api/v2/push/send'
EXPO_RECEIPTS = 'https://exp.host/--/api/v2/push/getReceipts'

TIPO_ASISTENCIA = RecordatorioTurno.Tipo.ASISTENCIA
TIPO_CONFIRMAR = RecordatorioTurno.Tipo.CONFIRMAR_TURNO


def headers():
    h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if settings.EXPO_ACCESS_TOKEN:
        h['Authorization'] = f'Bearer {settings.EXPO_ACCESS_TOKEN}'
    return h


def _dispositivos_paciente(user_id, now):
    return DispositivoPush.objects.filter(
        activo=True,
        sesion__user_id=user_id,
        sesion__revocada=False,
        sesion__expira_en__gt=now,
        sesion__user__is_active=True,
    )


def preparar_recordatorios_asistencia(now=None):
    """Push ~24 hs para turnos ya CONFIRMADO sin asistencia confirmada."""
    now = now or timezone.now()
    turnos = Turno.objects.filter(
        estado=Turno.Estado.CONFIRMADO,
        fecha_hora_inicio__gt=now,
        fecha_hora_inicio__lte=now + timedelta(hours=24),
        asistencia_confirmada_en__isnull=True,
        paciente__user__isnull=False,
    ).select_related('paciente')
    count = 0
    for turno in turnos.iterator():
        for dispositivo in _dispositivos_paciente(turno.paciente.user_id, now):
            _, created = RecordatorioTurno.objects.get_or_create(
                turno=turno,
                dispositivo=dispositivo,
                fecha_turno=turno.fecha_hora_inicio,
                tipo=TIPO_ASISTENCIA,
                defaults={'proximo_intento': now},
            )
            count += created
    return count


def preparar_recordatorios_confirmacion(now=None):
    """Push para turnos RESERVADO desde pasado mañana (confirmar estado en la app)."""
    now = now or timezone.now()
    pasado_manana = timezone.localdate() + timedelta(days=2)
    umbral = timezone.make_aware(datetime.combine(pasado_manana, dtime.min))
    turnos = Turno.objects.filter(
        estado=Turno.Estado.RESERVADO,
        fecha_hora_inicio__gte=umbral,
        paciente__user__isnull=False,
    ).select_related('paciente')
    count = 0
    for turno in turnos.iterator():
        for dispositivo in _dispositivos_paciente(turno.paciente.user_id, now):
            _, created = RecordatorioTurno.objects.get_or_create(
                turno=turno,
                dispositivo=dispositivo,
                fecha_turno=turno.fecha_hora_inicio,
                tipo=TIPO_CONFIRMAR,
                defaults={'proximo_intento': now},
            )
            count += created
    return count


def preparar_recordatorios(now=None):
    """Prepara ambos tipos de recordatorio. Compatibilidad con el comando periódico."""
    now = now or timezone.now()
    return preparar_recordatorios_asistencia(now) + preparar_recordatorios_confirmacion(now)


def vigente(recordatorio, turno, dispositivo, now):
    if not (
        turno.fecha_hora_inicio == recordatorio.fecha_turno
        and turno.fecha_hora_inicio > now
        and turno.paciente_id
        and turno.paciente.user_id == dispositivo.sesion.user_id
        and dispositivo.activo
        and not dispositivo.sesion.revocada
        and dispositivo.sesion.expira_en > now
        and dispositivo.sesion.user.is_active
    ):
        return False
    tipo = getattr(recordatorio, 'tipo', None) or TIPO_ASISTENCIA
    if tipo == TIPO_CONFIRMAR:
        return turno.estado == Turno.Estado.RESERVADO
    return (
        turno.estado == Turno.Estado.CONFIRMADO
        and not turno.asistencia_confirmada_en
    )


def _cuerpo_y_data(recordatorio, turno):
    tipo = getattr(recordatorio, 'tipo', None) or TIPO_ASISTENCIA
    if tipo == TIPO_CONFIRMAR:
        return (
            'Tenés un turno reservado. Abrí la app para confirmarlo. '
            'Si no podés ir, contactá a secretaría para liberar el horario.',
            {
                'turno_id': turno.pk,
                'institucion': settings.MOBILE_INSTITUTION_CODE,
                'tipo': 'confirmar_turno',
            },
        )
    return (
        'Tenés un turno próximo. Abrí la app para confirmar tu asistencia. '
        'Si necesitás cancelar, contactá a secretaría.',
        {
            'turno_id': turno.pk,
            'institucion': settings.MOBILE_INSTITUTION_CODE,
            'tipo': 'asistencia',
        },
    )


def enviar_pendientes(now=None, limit=100):
    if not settings.MOBILE_PUSH_ENABLED:
        return 0
    now = now or timezone.now()
    ids = list(
        RecordatorioTurno.objects.filter(estado='PENDIENTE', proximo_intento__lte=now)
        .order_by('proximo_intento')
        .values_list('id', flat=True)[:limit]
    )
    enviados = 0
    for pk in ids:
        with transaction.atomic():
            r = RecordatorioTurno.objects.select_for_update().get(pk=pk)
            if r.estado != 'PENDIENTE' or r.proximo_intento > now:
                continue
            turno = Turno.objects.select_for_update().get(pk=r.turno_id)
            # Evitar select_related en el FOR UPDATE (paciente puede ser NULL → outer join).
            turno = Turno.objects.select_related('paciente').get(pk=turno.pk)
            dispositivo = DispositivoPush.objects.select_related('sesion__user').get(
                pk=r.dispositivo_id
            )
            if not vigente(r, turno, dispositivo, now):
                r.estado = 'OMITIDO'
                r.save()
                continue
            r.intentos += 1
            body, data = _cuerpo_y_data(r, turno)
            try:
                response = requests.post(
                    EXPO_SEND,
                    headers=headers(),
                    timeout=10,
                    json={
                        'to': dispositivo.token,
                        'title': f'SYNESIS movil · {settings.MOBILE_INSTITUTION_NAME}',
                        'body': body,
                        'data': data,
                        'sound': 'default',
                        'channelId': 'turnos',
                        'ttl': max(1, int((turno.fecha_hora_inicio - now).total_seconds())),
                    },
                )
                response.raise_for_status()
                payload = response.json().get('data', {})
                if not isinstance(payload, dict):
                    raise ValueError('Formato inválido')
                if payload.get('status') == 'ok' and payload.get('id'):
                    r.ticket = str(payload['id'])[:128]
                    r.error_codigo = ''
                    enviados += 1
                    if r.tipo == TIPO_CONFIRMAR:
                        # Reintento diario hasta confirmar / cancelar / vencer.
                        r.estado = 'PENDIENTE'
                        r.proximo_intento = now + timedelta(days=1)
                    else:
                        r.estado = 'ACEPTADO'
                else:
                    code = (payload.get('details') or {}).get('error', 'ProviderError')
                    r.error_codigo = (
                        code
                        if code
                        in (
                            'DeviceNotRegistered',
                            'MessageRateExceeded',
                            'InvalidCredentials',
                            'MessageTooBig',
                        )
                        else 'ProviderError'
                    )
                    if code == 'DeviceNotRegistered':
                        dispositivo.activo = False
                        dispositivo.save(update_fields=['activo'])
                    r.estado = (
                        'PENDIENTE'
                        if code == 'MessageRateExceeded' and r.intentos < 5
                        else 'ERROR'
                    )
                    r.proximo_intento = now + timedelta(minutes=min(60, 2**r.intentos))
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                r.error_codigo = 'TransportError'
                r.estado = 'PENDIENTE' if r.intentos < 5 else 'ERROR'
                r.proximo_intento = now + timedelta(minutes=min(60, 2**r.intentos))
            else:
                if r.estado == 'ACEPTADO':
                    r.proximo_intento = now + timedelta(minutes=min(60, 2**r.intentos))
            r.save()
    return enviados


def consultar_recibos(now=None, limit=100):
    if not settings.MOBILE_PUSH_ENABLED:
        return 0
    now = now or timezone.now()
    pendientes = list(
        RecordatorioTurno.objects.filter(
            estado='ACEPTADO', actualizado_en__lte=now - timedelta(minutes=15)
        ).exclude(ticket='')[:limit]
    )
    if not pendientes:
        return 0
    try:
        response = requests.post(
            EXPO_RECEIPTS,
            headers=headers(),
            timeout=10,
            json={'ids': [r.ticket for r in pendientes]},
        )
        response.raise_for_status()
        data = response.json().get('data') or {}
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return 0
    actualizados = 0
    for r in pendientes:
        info = data.get(r.ticket) if isinstance(data, dict) else None
        if not isinstance(info, dict):
            continue
        if info.get('status') == 'ok':
            r.estado = 'ENTREGADO'
            r.save(update_fields=['estado', 'actualizado_en'])
            actualizados += 1
        elif info.get('status') == 'error':
            details = info.get('details') or {}
            code = details.get('error', 'ProviderError')
            r.error_codigo = code if isinstance(code, str) else 'ProviderError'
            if code == 'DeviceNotRegistered':
                DispositivoPush.objects.filter(pk=r.dispositivo_id).update(activo=False)
            r.estado = 'ERROR'
            r.save(update_fields=['estado', 'error_codigo', 'actualizado_en'])
            actualizados += 1
    return actualizados
