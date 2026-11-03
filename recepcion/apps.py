import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RecepcionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recepcion'
    verbose_name = 'Recepción y sala de espera'

    def ready(self):
        # Diagnóstico LAN: si la IP configurada no matchea, avisar (no bloquea).
        try:
            from django.conf import settings

            if not getattr(settings, 'DEBUG', False):
                return
            from synesis.lan_env import parse_lan_ips

            configured = parse_lan_ips()
            if not configured:
                logger.warning(
                    'EMR_LAN_IPS vacío: kiosco/TV en Wi‑Fi pueden fallar. '
                    'En Windows: powershell -File scripts/sync_lan_ip.ps1'
                )
        except Exception:
            pass
