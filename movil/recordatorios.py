"""Recordatorios con registro persistente, reintentos y recibos del proveedor.

ACEPTADO/ENTREGADO no significan que el usuario haya leído la notificación.
"""
from datetime import timedelta
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from turnos.models import Turno
from .models import DispositivoPush, RecordatorioTurno

EXPO_SEND = 'https://exp.host/--/api/v2/push/send'
EXPO_RECEIPTS = 'https://exp.host/--/api/v2/push/getReceipts'


def headers():
    h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if settings.EXPO_ACCESS_TOKEN:
        h['Authorization'] = f'Bearer {settings.EXPO_ACCESS_TOKEN}'
    return h


def preparar_recordatorios(now=None):
    now = now or timezone.now()
    turnos = Turno.objects.filter(estado__in=['RESERVADO', 'CONFIRMADO'],
        fecha_hora_inicio__gt=now, fecha_hora_inicio__lte=now+timedelta(hours=24),
        asistencia_confirmada_en__isnull=True, paciente__user__isnull=False).select_related('paciente')
    count = 0
    for turno in turnos.iterator():
        dispositivos = DispositivoPush.objects.filter(activo=True, sesion__user_id=turno.paciente.user_id,
            sesion__revocada=False, sesion__expira_en__gt=now, sesion__user__is_active=True)
        for dispositivo in dispositivos:
            _, created = RecordatorioTurno.objects.get_or_create(turno=turno, dispositivo=dispositivo,
                fecha_turno=turno.fecha_hora_inicio, defaults={'proximo_intento': now})
            count += created
    return count


def vigente(recordatorio, turno, dispositivo, now):
    return (turno.fecha_hora_inicio == recordatorio.fecha_turno and turno.fecha_hora_inicio > now
        and turno.estado in ('RESERVADO', 'CONFIRMADO') and not turno.asistencia_confirmada_en
        and turno.paciente_id and turno.paciente.user_id == dispositivo.sesion.user_id
        and dispositivo.activo and not dispositivo.sesion.revocada
        and dispositivo.sesion.expira_en > now and dispositivo.sesion.user.is_active)


def enviar_pendientes(now=None, limit=100):
    if not settings.MOBILE_PUSH_ENABLED:
        return 0
    now = now or timezone.now()
    ids = list(RecordatorioTurno.objects.filter(estado='PENDIENTE', proximo_intento__lte=now)
               .order_by('proximo_intento').values_list('id', flat=True)[:limit])
    enviados = 0
    for pk in ids:
        with transaction.atomic():
            r = RecordatorioTurno.objects.select_for_update().get(pk=pk)
            if r.estado != 'PENDIENTE' or r.proximo_intento > now:
                continue
            turno = Turno.objects.select_for_update().get(pk=r.turno_id)
            dispositivo = DispositivoPush.objects.select_related('sesion__user').get(pk=r.dispositivo_id)
            if not vigente(r, turno, dispositivo, now):
                r.estado = 'OMITIDO'; r.save(); continue
            r.intentos += 1
            try:
                response = requests.post(EXPO_SEND, headers=headers(), timeout=10, json={
                    'to': dispositivo.token, 'title': f'SYNESIS movil · {settings.MOBILE_INSTITUTION_NAME}',
                    'body': 'Tenés un turno próximo. Abrí la app para confirmar, cancelar o reprogramar.',
                    'data': {'turno_id': turno.pk, 'institucion': settings.MOBILE_INSTITUTION_CODE}, 'sound': 'default', 'channelId': 'turnos',
                    'ttl': max(1, int((turno.fecha_hora_inicio-now).total_seconds())),
                })
                response.raise_for_status()
                data = response.json().get('data', {})
                if not isinstance(data, dict):
                    raise ValueError('Formato inválido')
                if data.get('status') == 'ok' and data.get('id'):
                    r.ticket = str(data['id'])[:128]; r.estado = 'ACEPTADO'; r.error_codigo = ''; enviados += 1
                else:
                    code = (data.get('details') or {}).get('error', 'ProviderError')
                    r.error_codigo = code if code in ('DeviceNotRegistered', 'MessageRateExceeded', 'InvalidCredentials', 'MessageTooBig') else 'ProviderError'
                    if code == 'DeviceNotRegistered':
                        dispositivo.activo = False; dispositivo.save(update_fields=['activo'])
                    r.estado = 'PENDIENTE' if code == 'MessageRateExceeded' and r.intentos < 5 else 'ERROR'
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                # Nunca registrar token ni payload del proveedor. Reintento acotado.
                r.error_codigo = 'TransportError'
                r.estado = 'PENDIENTE' if r.intentos < 5 else 'ERROR'
            r.proximo_intento = now + timedelta(minutes=min(60, 2**r.intentos))
            r.save()
    return enviados


def consultar_recibos(now=None, limit=100):
    if not settings.MOBILE_PUSH_ENABLED:
        return 0
    now = now or timezone.now()
    pendientes = list(RecordatorioTurno.objects.filter(estado='ACEPTADO',
        actualizado_en__lte=now-timedelta(minutes=15)).exclude(ticket='')[:limit])
    if not pendientes:
        return 0
    try:
        response = requests.post(EXPO_RECEIPTS, headers=headers(), timeout=10,
                                 json={'ids': [r.ticket for r in pendientes]})
        response.raise_for_status()
        recibos = response.json().get('data', {})
        if not isinstance(recibos, dict):
            return 0
    except (requests.RequestException, ValueError, AttributeError):
        return 0
    count = 0
    for r in pendientes:
        recibo = recibos.get(r.ticket)
        if not isinstance(recibo, dict):
            if r.actualizado_en < now-timedelta(hours=24):
                r.estado='ERROR'; r.error_codigo='ReceiptUnavailable'; r.save()
            continue
        if recibo.get('status') == 'ok':
            r.estado='ENTREGADO'; r.error_codigo=''
        else:
            r.estado='ERROR'; r.error_codigo='ReceiptError'
            if (recibo.get('details') or {}).get('error') == 'DeviceNotRegistered':
                DispositivoPush.objects.filter(pk=r.dispositivo_id).update(activo=False)
                r.error_codigo='DeviceNotRegistered'
        r.save(); count += 1
    return count
