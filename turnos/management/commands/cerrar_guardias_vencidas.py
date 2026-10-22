"""
Cierra atenciones de guardia ABIERTAS con más de N horas (default 24).

Uso:
  python manage.py cerrar_guardias_vencidas
  python manage.py cerrar_guardias_vencidas --dry-run
  python manage.py cerrar_guardias_vencidas --horas 24

Programar en cron del host (p. ej. cada hora) para liberar pacientes
bloqueados aunque nadie intente una nueva atención.
"""
from django.core.management.base import BaseCommand

from turnos.situacion_paciente import GUARDIA_MAX_HORAS_ABIERTA, cerrar_guardias_vencidas


class Command(BaseCommand):
    help = (
        "Cierra guardias ABIERTAS vencidas (>N horas desde fecha_admision) "
        "para no bloquear nuevas atenciones ni internaciones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--horas",
            type=int,
            default=GUARDIA_MAX_HORAS_ABIERTA,
            help=f"Horas máximas abiertas (default {GUARDIA_MAX_HORAS_ABIERTA}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo listar IDs que se cerrarían, sin persistir.",
        )

    def handle(self, *args, **options):
        horas = options["horas"]
        dry_run = options["dry_run"]
        ids = cerrar_guardias_vencidas(horas=horas, dry_run=dry_run)
        modo = "dry-run" if dry_run else "cerradas"
        if not ids:
            self.stdout.write(self.style.SUCCESS(f"Sin guardias vencidas ({modo})."))
            return
        self.stdout.write(
            self.style.WARNING(f"Guardias {modo} ({len(ids)}, >{horas}h): {ids}")
        )
