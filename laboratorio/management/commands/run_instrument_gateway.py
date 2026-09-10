"""Escucha ASTM TCP para una InterfazInstrumento."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from laboratorio.instrumentos_gateway import serve_tcp
from laboratorio.models_instrumentos import InterfazInstrumento


class Command(BaseCommand):
    help = "Gateway ASTM TCP (un proceso por interfaz). No abrir COM desde Docker."

    def add_arguments(self, parser):
        parser.add_argument("--driver", default="CM260", help="CM260 o SYSMEX_XP300")
        parser.add_argument("--host", default="", help="Override LIMS_INSTRUMENT_LISTEN_HOST")
        parser.add_argument("--port", type=int, default=0, help="Override listen port")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignora LIMS_INSTRUMENT_ENABLED=false (solo desarrollo).",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "LIMS_INSTRUMENT_ENABLED", False) and not options["force"]:
            raise CommandError(
                "LIMS_INSTRUMENT_ENABLED=false. Use --force en desarrollo o active el flag."
            )
        driver = (options["driver"] or "CM260").strip().upper()
        interfaz = InterfazInstrumento.objects.filter(driver=driver, activo=True).first()
        if interfaz is None:
            raise CommandError(f"No hay interfaz activa driver={driver}. Ejecute seed_instrumentos.")
        host = options["host"] or settings.LIMS_INSTRUMENT_LISTEN_HOST
        port = options["port"] or interfaz.puerto or settings.LIMS_INSTRUMENT_LISTEN_PORT
        self.stdout.write(f"Escuchando ASTM {driver} en {host}:{port}")
        serve_tcp(interfaz, host, int(port))
