"""
Compara todo_labwin.csv contra órdenes LW en BD. SOLO LECTURA.

No escribe PostgreSQL. Solo imprime conteos agregados (sin PHI).
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from laboratorio.labwin_reconcile import reconcile_orders_against_db, stats_as_public_dict


class Command(BaseCommand):
    help = (
        "Reconciliación LabWin CSV ↔ SolicitudExamen LW (solo lectura). "
        "Emite únicamente estadísticas agregadas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            nargs="?",
            default="data/icpl/todo_labwin.csv",
            help="Ruta al CSV LabWin",
        )
        parser.add_argument("--encoding", default="utf-8-sig")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo no existe: {csv_path}")

        self.stdout.write("RECONCILE LABWIN: SOLO LECTURA. Sin PHI.")
        self.stdout.write(f"Archivo: {csv_path.name}")
        stats = reconcile_orders_against_db(csv_path, encoding=options["encoding"])
        public = stats_as_public_dict(stats)
        for key in sorted(public):
            self.stdout.write(f"  {key}={public[key]}")
        self.stdout.write(self.style.SUCCESS("Reconciliación finalizada (sin escrituras)."))
