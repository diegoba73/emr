"""Crea interfaces CM260 / Sysmex y mapeos de analito."""
from django.core.management.base import BaseCommand

from laboratorio.instrumentos_seed import seed_instrumentos_default


class Command(BaseCommand):
    help = "Crea InterfazInstrumento CM260/Sysmex y mapeos de analito (idempotente)."

    def handle(self, *args, **options):
        result = seed_instrumentos_default()
        for driver, (creados, omitidos) in result.items():
            self.stdout.write(
                f"{driver}: mapeos nuevos={creados} omitidos_sin_examen={omitidos}"
            )
        self.stdout.write(self.style.SUCCESS("seed_instrumentos listo."))
