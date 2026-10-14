"""Notificaciones al paciente cuando secretaría reprograma un turno.

Push Expo (si hay dispositivo) + WhatsApp (Twilio si está configurado; si no, enlace wa.me).
Los fallos de notificación no abortan la reprogramación.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import timezone as dt_timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

EXPO_SEND = 'https://exp.host/--/api/v2/push/send'


@dataclass(frozen=True)
class NotificacionReprogramacion:
    whatsapp_enviado: bool
    whatsapp_url: str | None
    push_enviados: int
    detalle: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'whatsapp_enviado': self.whatsapp_enviado,
            'whatsapp_url': self.whatsapp_url,
            'push_enviados': self.push_enviados,
            'detalle': self.detalle,
        }


def _normalize_whatsapp_phone(telefono: str | None) -> str | None:
    if not telefono:
        return None
    digits = re.sub(r'\D', '', telefono)
    if not digits:
        return None
    if digits.startswith('0'):
        digits = '54' + digits[1:]
    elif len(digits) <= 10 and not digits.startswith('54'):
        digits = '54' + digits
    return digits


def _enlace_whatsapp_web(telefono: str, mensaje: str) -> str:
    return f'https://wa.me/{telefono}?text={quote(mensaje)}'


def _intentar_twilio_whatsapp(telefono: str, mensaje: str) -> tuple[bool, str | None]:
    sid = os.getenv('TWILIO_ACCOUNT_SID', '').strip()
    token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
    from_wa = os.getenv('TWILIO_WHATSAPP_FROM', '').strip()
    if not (sid and token and from_wa):
        return False, None
    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
    except ImportError:
        return False, 'Paquete twilio no instalado en el servidor.'
    try:
        Client(sid, token).messages.create(
            from_=from_wa,
            to=f'whatsapp:+{telefono}',
            body=mensaje,
        )
        return True, None
    except Exception as exc:
        logger.exception('Error enviando WhatsApp de reprogramación vía Twilio')
        return False, f'Twilio rechazó el envío: {exc}'


def _tz_local():
    name = getattr(settings, 'TIME_ZONE', None) or 'America/Argentina/Buenos_Aires'
    try:
        return ZoneInfo(name)
    except Exception:
        return dt_timezone.utc


def _formato_fecha_hora(dt) -> str:
    if dt is None:
        return '—'
    if timezone.is_aware(dt):
        local = timezone.localtime(dt, _tz_local())
    else:
        local = dt
    return local.strftime('%d/%m/%Y %H:%M')


def _mensaje_paciente(turno) -> str:
    cuando = _formato_fecha_hora(turno.fecha_hora_inicio)
    medico = ''
    if turno.medico_id:
        med = turno.medico
        medico = getattr(med, 'nombre_completo', None) or str(med)
    institucion = getattr(settings, 'MOBILE_INSTITUTION_NAME', None) or 'SYNESIS'
    partes = [
        f'Hola, le informamos que su turno en {institucion} fue reprogramado.',
        f'Nueva fecha y hora: {cuando}.',
    ]
    if medico:
        partes.append(f'Médico: {medico}.')
    partes.append('Ante cualquier duda, comuníquese con secretaría.')
    return ' '.join(partes)


def _expo_headers() -> dict[str, str]:
    h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    token = getattr(settings, 'EXPO_ACCESS_TOKEN', None) or ''
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def _enviar_push(turno) -> int:
    if not getattr(settings, 'MOBILE_PUSH_ENABLED', False):
        return 0
    paciente = getattr(turno, 'paciente', None)
    user_id = getattr(paciente, 'user_id', None) if paciente else None
    if not user_id:
        return 0

    from movil.models import DispositivoPush

    now = timezone.now()
    dispositivos = DispositivoPush.objects.filter(
        activo=True,
        sesion__user_id=user_id,
        sesion__revocada=False,
        sesion__expira_en__gt=now,
        sesion__user__is_active=True,
    )
    body = (
        f'Su turno fue reprogramado para el {_formato_fecha_hora(turno.fecha_hora_inicio)}. '
        'Abrí la app para ver el detalle.'
    )
    title = f'SYNESIS · turno reprogramado'
    enviados = 0
    for dispositivo in dispositivos.iterator():
        try:
            response = requests.post(
                EXPO_SEND,
                headers=_expo_headers(),
                timeout=10,
                json={
                    'to': dispositivo.token,
                    'title': title,
                    'body': body,
                    'data': {
                        'turno_id': turno.pk,
                        'tipo': 'turno_reprogramado',
                        'institucion': getattr(settings, 'MOBILE_INSTITUTION_CODE', ''),
                    },
                    'sound': 'default',
                    'channelId': 'turnos',
                },
            )
            response.raise_for_status()
            data = response.json().get('data', {})
            if isinstance(data, dict) and data.get('status') == 'ok':
                enviados += 1
            elif isinstance(data, dict) and (data.get('details') or {}).get('error') == 'DeviceNotRegistered':
                dispositivo.activo = False
                dispositivo.save(update_fields=['activo'])
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            logger.exception('Error enviando push de reprogramación turno_id=%s', turno.pk)
    return enviados


def notificar_reprogramacion(turno) -> NotificacionReprogramacion:
    """Envía push y prepara/envía WhatsApp. Nunca lanza por fallos de canal."""
    mensaje = _mensaje_paciente(turno)
    push_enviados = 0
    try:
        push_enviados = _enviar_push(turno)
    except Exception:
        logger.exception('Fallo inesperado en push de reprogramación turno_id=%s', getattr(turno, 'pk', None))

    telefono_raw = ''
    if turno.paciente_id:
        telefono_raw = (getattr(turno.paciente, 'telefono', None) or '').strip()
    telefono = _normalize_whatsapp_phone(telefono_raw)
    if not telefono:
        return NotificacionReprogramacion(
            whatsapp_enviado=False,
            whatsapp_url=None,
            push_enviados=push_enviados,
            detalle='Paciente sin teléfono válido para WhatsApp.',
        )

    enviado, error = _intentar_twilio_whatsapp(telefono, mensaje)
    if enviado:
        return NotificacionReprogramacion(
            whatsapp_enviado=True,
            whatsapp_url=None,
            push_enviados=push_enviados,
            detalle=None,
        )

    url = _enlace_whatsapp_web(telefono, mensaje)
    return NotificacionReprogramacion(
        whatsapp_enviado=False,
        whatsapp_url=url,
        push_enviados=push_enviados,
        detalle=error,
    )
