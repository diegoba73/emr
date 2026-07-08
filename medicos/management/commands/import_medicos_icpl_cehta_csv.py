from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pathlib import Path

from medicos.icpl_cehta_csv import (
    build_areas_interes,
    canonical_especialidad_nombre,
    load_icpl_medicos_from_csv,
    _normalize_key,
    _normalize_matricula,
)
from medicos.models import Especialidad, Medico


class Command(BaseCommand):
    help = (
        "Importa médicos ICPL/CEHTA Trelew desde CSV, creando especialidades "
        "faltantes y vinculando cada médico a su especialidad principal."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            nargs="?",
            default="data/icpl/medicos_icpl_cehta_trelew.csv",
            help="Ruta al CSV. Por defecto: data/icpl/medicos_icpl_cehta_trelew.csv",
        )
        parser.add_argument(
            "--encoding",
            default="utf-8-sig",
            help="Encoding del archivo (por defecto utf-8-sig).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analiza el archivo sin escribir en la base.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Actualiza médicos existentes (por matrícula o nombre).",
        )

    def _resolve_especialidad(self, nombre: str) -> tuple[Especialidad | None, bool]:
        canon = canonical_especialidad_nombre(nombre)
        if not canon:
            return None, False

        existing = Especialidad.objects.filter(nombre__iexact=canon).first()
        if existing:
            return existing, False

        return (
            Especialidad.objects.create(
                nombre=canon,
                descripcion=f"Especialidad importada ICPL/CEHTA — {canon}",
            ),
            True,
        )

    def _find_existing_medico(self, *, matricula: str, apellido: str, nombres: str) -> Medico | None:
        medico = Medico.objects.filter(matricula=matricula).first()
        if medico:
            return medico
        if apellido and nombres:
            return (
                Medico.objects.filter(apellido__iexact=apellido, nombre__iexact=nombres)
                .order_by("id")
                .first()
            )
        return None

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo no existe: {csv_path}")

        medicos, stats = load_icpl_medicos_from_csv(csv_path, encoding=options["encoding"])

        self.stdout.write(f"Archivo: {csv_path}")
        self.stdout.write(f"  Filas CSV: {stats.rows_parsed}")
        self.stdout.write(f"  Médicos únicos (deduplicados): {stats.unique_medicos}")
        if stats.especialidades_detectadas:
            self.stdout.write(
                "  Especialidades detectadas: "
                + ", ".join(sorted(stats.especialidades_detectadas))
            )

        if stats.warnings:
            self.stdout.write(self.style.WARNING("Advertencias:"))
            for warning in stats.warnings:
                self.stdout.write(f"  - {warning}")

        if options["dry_run"]:
            for row in list(medicos.values())[:5]:
                esp = canonical_especialidad_nombre(row.especialidad_principal) or "—"
                mat = _normalize_matricula(row.matricula_profesional, import_id=row.import_id)
                self.stdout.write(
                    f"  Ejemplo: {row.apellido}, {row.nombres} | {esp} | mat {mat}"
                )
            self.stdout.write(self.style.SUCCESS("Dry-run: no se modificó la base."))
            return

        created = 0
        updated = 0
        skipped = 0
        especialidades_creadas = 0
        especialidad_cache: dict[str, tuple[Especialidad | None, bool]] = {}

        with transaction.atomic():
            for row in medicos.values():
                matricula = _normalize_matricula(
                    row.matricula_profesional,
                    import_id=row.import_id,
                )
                if not matricula:
                    skipped += 1
                    continue

                esp_key = _normalize_key(row.especialidad_principal)
                if esp_key not in especialidad_cache:
                    especialidad_cache[esp_key] = self._resolve_especialidad(
                        row.especialidad_principal
                    )
                especialidad, esp_created = especialidad_cache[esp_key]
                if esp_created:
                    especialidades_creadas += 1

                defaults = {
                    "nombre": row.nombres or None,
                    "apellido": row.apellido or None,
                    "especialidad": especialidad,
                    "areas_interes_ia": build_areas_interes(row),
                }

                existing = self._find_existing_medico(
                    matricula=matricula,
                    apellido=row.apellido,
                    nombres=row.nombres,
                )
                if existing:
                    if not options["update_existing"]:
                        skipped += 1
                        continue
                    for field, value in defaults.items():
                        setattr(existing, field, value)
                    if existing.matricula != matricula:
                        old_is_placeholder = existing.matricula.startswith("MED-")
                        new_is_placeholder = matricula.startswith("MED-")
                        if (old_is_placeholder and not new_is_placeholder) or (
                            not Medico.objects.filter(matricula=matricula).exclude(pk=existing.pk).exists()
                            and not new_is_placeholder
                        ):
                            existing.matricula = matricula
                    existing.save()
                    updated += 1
                    continue

                Medico.objects.create(matricula=matricula, **defaults)
                created += 1

        con_especialidad = Medico.objects.filter(especialidad__isnull=False).count()
        self.stdout.write(self.style.SUCCESS("Importación completada."))
        self.stdout.write(f"  ➕ Nuevos: {created}")
        self.stdout.write(f"  ♻️ Actualizados: {updated}")
        self.stdout.write(f"  ⏭️ Omitidos: {skipped}")
        self.stdout.write(f"  🏷️ Especialidades nuevas: {especialidades_creadas}")
        self.stdout.write(f"  🩺 Médicos con especialidad en BD: {con_especialidad}")
