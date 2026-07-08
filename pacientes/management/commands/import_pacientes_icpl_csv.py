from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pathlib import Path

from pacientes.icpl_csv import (
    build_observaciones,
    load_icpl_patients_from_csv,
    summarize_icpl_coverage,
)
from pacientes.models import Paciente


class Command(BaseCommand):
    help = (
        "Importa pacientes desde el CSV de internaciones ICPL (PACIENTES.csv). "
        "Deduplica por DNI usando el ingreso más reciente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            nargs="?",
            default="data/icpl/PACIENTES.csv",
            help="Ruta al CSV (;). Por defecto: data/icpl/PACIENTES.csv",
        )
        parser.add_argument(
            "--encoding",
            default="latin-1",
            help="Encoding del archivo (por defecto latin-1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analiza el archivo sin escribir en la base.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Actualiza pacientes existentes (por DNI) con datos del CSV.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Tamaño de lote para bulk_create (por defecto 500).",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo no existe: {csv_path}")

        patients, stats = load_icpl_patients_from_csv(
            csv_path,
            encoding=options["encoding"],
        )

        self.stdout.write(f"Archivo: {csv_path}")
        self.stdout.write(f"  Líneas leídas: {stats.lines_read}")
        self.stdout.write(f"  Filas de internación válidas: {stats.rows_parsed}")
        self.stdout.write(f"  Filas omitidas: {stats.rows_skipped}")
        self.stdout.write(f"  Pacientes únicos (por DNI): {stats.unique_patients}")

        coverage = summarize_icpl_coverage(patients)
        total = stats.unique_patients or 1
        self.stdout.write(
            f"  Con obra social: {coverage['with_obra_social']}/{total}"
        )
        self.stdout.write(
            f"  Con N° afiliado: {coverage['with_numero_afiliado']}/{total}"
        )
        top_obras = coverage["top_obras_sociales"]
        if top_obras:
            self.stdout.write("  Obras sociales más frecuentes:")
            for nombre, cantidad in top_obras:
                self.stdout.write(f"    - {nombre}: {cantidad}")

        if options["dry_run"]:
            sample = next(iter(patients.values()), None)
            if sample and sample.obra_social:
                self.stdout.write(
                    "  Ejemplo: "
                    f"{sample.apellido}, {sample.nombre} (DNI {sample.dni}) — "
                    f"{sample.obra_social}"
                    + (f" / afiliado {sample.numero_afiliado}" if sample.numero_afiliado else "")
                )

        if stats.warnings:
            self.stdout.write(self.style.WARNING("Advertencias (muestra):"))
            for warning in stats.warnings:
                self.stdout.write(f"  - {warning}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run: no se modificó la base."))
            return

        existing = set(
            Paciente.objects.filter(
                dni__in=patients.keys(),
            ).values_list("dni", flat=True)
        )

        to_create: list[Paciente] = []
        updated = 0
        skipped_existing = 0

        for dni, row in patients.items():
            defaults = {
                "nombre": row.nombre or "Sin nombre",
                "apellido": row.apellido or "Sin apellido",
                "fecha_nacimiento": row.fecha_nacimiento,
                "sexo": row.sexo or None,
                "telefono": row.telefono or None,
                "direccion": row.direccion or None,
                "obra_social": row.obra_social or None,
                "numero_afiliado": row.numero_afiliado or None,
                "observaciones": build_observaciones(row),
            }

            if dni in existing:
                if not options["update_existing"]:
                    skipped_existing += 1
                    continue
                Paciente.objects.filter(dni=dni).update(**defaults)
                updated += 1
                continue

            to_create.append(Paciente(dni=dni, **defaults))

        created = 0
        batch_size = max(1, options["batch_size"])
        with transaction.atomic():
            for start in range(0, len(to_create), batch_size):
                batch = to_create[start : start + batch_size]
                Paciente.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)

        imported_dnis = list(patients.keys())
        with_obra_db = (
            Paciente.objects.filter(dni__in=imported_dnis)
            .exclude(obra_social__isnull=True)
            .exclude(obra_social="")
            .count()
        )

        self.stdout.write(self.style.SUCCESS("Importación completada."))
        self.stdout.write(f"  ➕ Nuevos: {created}")
        self.stdout.write(f"  ♻️ Actualizados: {updated}")
        self.stdout.write(f"  ⏭️ Existentes sin cambios: {skipped_existing}")
        self.stdout.write(f"  🏥 Con obra social en BD: {with_obra_db}/{len(imported_dnis)}")
