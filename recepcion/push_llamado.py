"""Push al paciente cuando secretaría lo llama (best-effort)."""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.utils import timezone

from .services import nombre_publico_paciente

logger = logging.getLogger(__name__)
EXPO_SEND = 'https://exp.host/--/api/v2/push/send'


def enviar_push_llamado(llegada) -> int:
    if not getattr(settings, 'MOBILE_PUSH_ENABLED', False):
        return 0
    paciente = llegada.paciente
    user_id = getattr(paciente, 'user_id', None)
    if not user_id:
        return 0
    try:
        from movil.models import DispositivoPush
    except Exception:
        return 0

    now = timezone.now()
    dispositivos = DispositivoPush.objects.filter(
        activo=True,
        sesion__user_id=user_id,
        sesion__revocada=False,
        sesion__expira_en__gt=now,
        sesion__user__is_active=True,
    )
    destino = llegada.destino_label or (
        llegada.destino_recurso.nombre if llegada.destino_recurso_id else 'recepción'
    )
    title = f'SYNESIS · {getattr(settings, "MOBILE_INSTITUTION_NAME", "Clínica")}'
    body = f'Te llaman. Andá a {destino}.'
    enviados = 0
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    token = getattr(settings, 'EXPO_ACCESS_TOKEN', None)
    if token:
        headers['Authorization'] = f'Bearer {token}'
    for dispositivo in dispositivos:
        try:
            r = requests.post(
                EXPO_SEND,
                headers=headers,
                timeout=8,
                json={
                    'to': dispositivo.token,
                    'title': title,
                    'body': body,
                    'sound': 'default',
                    'channelId': 'turnos',
                    'priority': 'high',
                    'ttl': 120,
                    # Android: canal "turnos" (vibración + sonido) lo crea la app al Activar avisos.
                    'mutableContent': True,
                    'data': {
                        'tipo': 'llamado_medico',
                        'llegada_id': llegada.pk,
                        'destino': destino,
                        'paciente': nombre_publico_paciente(paciente),
                        'numero_orden_dia': llegada.numero_orden_dia,
                        'codigo_llamado': llegada.codigo_llamado or '',
                    },
                },
            )
            if r.ok:
                enviados += 1
        except Exception as e:
            logger.warning('push llamado falló: %s', e)
    return enviados
