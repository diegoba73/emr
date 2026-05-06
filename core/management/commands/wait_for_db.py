"""
Comando de gestión Django para esperar a que la base de datos esté disponible.
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError
try:
    from psycopg2 import OperationalError as Psycopg2OpError
except ImportError:
    Psycopg2OpError = OperationalError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Comando Django que pausa la ejecución hasta que la base de datos esté disponible."""

    def handle(self, *args, **options):
        """Ejecuta el comando."""
        self.stdout.write('Esperando a que la base de datos esté disponible...')
        db_conn = None
        while not db_conn:
            try:
                connection.ensure_connection()
                db_conn = True
            except (Psycopg2OpError, OperationalError):
                logger.warning('La base de datos no está disponible, esperando 1 segundo...')
                time.sleep(1)

        logger.info('Base de datos disponible!')
        self.stdout.write(self.style.SUCCESS('Base de datos disponible!'))

