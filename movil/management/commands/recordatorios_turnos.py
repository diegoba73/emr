from django.conf import settings
from django.core.management.base import BaseCommand
from movil.recordatorios import preparar_recordatorios, enviar_pendientes, consultar_recibos


class Command(BaseCommand):
    help = 'Procesa recordatorios de turnos a 24 horas. Ejecutar periódicamente (cada 5 minutos).'

    def handle(self, *args, **options):
        if not settings.MOBILE_PUSH_ENABLED:
            self.stdout.write('Recordatorios desactivados: MOBILE_PUSH_ENABLED=False.')
            return
        preparados = preparar_recordatorios()
        enviados = enviar_pendientes()
        recibos = consultar_recibos()
        self.stdout.write(f'Preparados: {preparados}; aceptados por proveedor: {enviados}; recibos: {recibos}.')
