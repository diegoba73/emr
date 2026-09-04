"""Borra datos transaccionales LIMS en desarrollo local (NO producción).

Uso (solo Docker local):
  python manage.py wipe_lims_transaccional --confirmo-wipe-local
  python manage.py wipe_lims_transaccional --confirmo-wipe-local --con-calibraciones

Borra: micro transaccional, muestras/eventos, resultados, solicitudes LIMS,
corridas/puntos QC, materiales/lotes, productos/lotes/targets.
NO borra: pacientes, exámenes, paneles, equipos, catálogos micro, inventario.
"""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Wipe local LIMS transaccional (muestras, órdenes, resultados, QC). Requiere --confirmo-wipe-local."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmo-wipe-local",
            action="store_true",
            help="Obligatorio. Confirma borrado destructivo solo en entorno local.",
        )
        parser.add_argument(
            "--con-calibraciones",
            action="store_true",
            help="También borra Calibracion (historial de calibradores).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo cuenta filas; no borra.",
        )

    def _assert_local_safe(self):
        if not getattr(settings, "DEBUG", False):
            raise CommandError("Abortado: DEBUG=False (posible producción).")
        allowed = {"localhost", "127.0.0.1", "db", "emr_postgres", "postgres"}
        db_host = (settings.DATABASES.get("default") or {}).get("HOST") or ""
        if db_host.strip().lower() not in allowed:
            raise CommandError(
                f"Abortado: DB_HOST={db_host!r} no es local Docker. "
                "Este comando solo corre contra localhost/db/emr_postgres."
            )
        db_name = (settings.DATABASES.get("default") or {}).get("NAME") or ""
        if db_name != "synesis_db":
            raise CommandError(
                f"Abortado: DB_NAME={db_name!r} distinto de synesis_db (BD local única)."
            )

    def handle(self, *args, **options):
        if not options["confirmo_wipe_local"]:
            raise CommandError(
                "Falta --confirmo-wipe-local. "
                "Hacé backup antes: bash scripts/backup_postgres_local.sh"
            )
        self._assert_local_safe()

        from laboratorio.models import (
            AisladoMicrobiologico,
            Antibiograma,
            Calibracion,
            CorridaQC,
            EstudioMicrobiologia,
            EventoMuestra,
            IdentificacionMicroorganismo,
            InformeMicrobiologia,
            LecturaCultivo,
            LoteControl,
            LoteProductoControl,
            MaterialControl,
            Muestra,
            ProductoControl,
            PuntoQC,
            ResultadoAntibiotico,
            ResultadoExamen,
            SiembraMicrobiologia,
            SolicitudExamen,
            TargetLoteControl,
        )

        steps = [
            ("ResultadoAntibiotico", ResultadoAntibiotico),
            ("Antibiograma", Antibiograma),
            ("IdentificacionMicroorganismo", IdentificacionMicroorganismo),
            ("AisladoMicrobiologico", AisladoMicrobiologico),
            ("InformeMicrobiologia", InformeMicrobiologia),
            ("LecturaCultivo", LecturaCultivo),
            ("SiembraMicrobiologia", SiembraMicrobiologia),
            ("EstudioMicrobiologia", EstudioMicrobiologia),
            ("EventoMuestra", EventoMuestra),
            ("ResultadoExamen", ResultadoExamen),
            ("Muestra", Muestra),
            ("SolicitudExamen", SolicitudExamen),
            ("PuntoQC", PuntoQC),
            ("CorridaQC", CorridaQC),
            ("TargetLoteControl", TargetLoteControl),
            ("LoteProductoControl", LoteProductoControl),
            ("ProductoControl", ProductoControl),
            ("LoteControl", LoteControl),
            ("MaterialControl", MaterialControl),
        ]
        if options["con_calibraciones"]:
            steps.append(("Calibracion", Calibracion))

        counts = [(name, model.objects.count()) for name, model in steps]
        self.stdout.write("Conteo previo:")
        for name, n in counts:
            self.stdout.write(f"  {name}: {n}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run: no se borró nada."))
            return

        with transaction.atomic():
            for name, model in steps:
                deleted, detail = model.objects.all().delete()
                self.stdout.write(f"  OK {name}: deleted={deleted} {detail}")

        self.stdout.write(
            self.style.SUCCESS(
                "Wipe LIMS OK. Catálogos/pacientes/equipos intactos. "
                "Sugerido: python manage.py seed_qc_demo"
            )
        )
