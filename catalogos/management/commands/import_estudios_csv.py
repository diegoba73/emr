from django.core.management.base import BaseCommand, CommandError
import csv
from pathlib import Path

from catalogos.models import EstudioDiagnostico


def normalizar_espacios(valor: str) -> str:
    if not valor:
        return ""
    return " ".join(valor.split()).strip()


class Command(BaseCommand):
    help = (
        "Importa estudios diagnósticos desde un CSV o archivo de texto. "
        "Cada fila debe contener el nombre del estudio en la primera columna."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Ruta absoluta o relativa al archivo de estudios.",
        )
        parser.add_argument(
            "--encoding",
            default="latin-1",
            help="Encoding del archivo (por defecto latin-1).",
        )
        parser.add_argument(
            "--delimiter",
            default=",",
            help="Delimitador del archivo (por defecto ',').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué cambios se harían sin escribir en la base.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Actualiza la descripción si ya existe el estudio.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo no existe: {csv_path}")

        encoding = options["encoding"]
        delimiter = options["delimiter"]
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        creados = 0
        actualizados = 0
        omitidos = 0
        errores: list[str] = []

        with csv_path.open(newline="", encoding=encoding) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            for indice, row in enumerate(reader, start=1):
                if not row:
                    continue
                nombre = normalizar_espacios(row[0]) if row else ""
                if not nombre:
                    omitidos += 1
                    continue

                descripcion = None
                if len(row) > 1 and row[1]:
                    descripcion = normalizar_espacios(row[1])
                if not descripcion:
                    descripcion = nombre

                try:
                    estudio = EstudioDiagnostico.objects.filter(nombre__iexact=nombre).first()
                    if not estudio:
                        if dry_run:
                            creados += 1
                        else:
                            EstudioDiagnostico.objects.create(
                                nombre=nombre,
                                descripcion=descripcion,
                                activo=True,
                            )
                            creados += 1
                        continue

                    cambios = False
                    if overwrite and descripcion and estudio.descripcion != descripcion:
                        cambios = True
                        if not dry_run:
                            estudio.descripcion = descripcion

                    if not estudio.activo:
                        cambios = True
                        if not dry_run:
                            estudio.activo = True

                    if cambios:
                        if dry_run:
                            actualizados += 1
                        else:
                            estudio.save(update_fields=["descripcion", "activo"])
                            actualizados += 1
                    else:
                        omitidos += 1
                except Exception as exc:
                    errores.append(f"Línea {indice}: {exc}")

        self.stdout.write(self.style.SUCCESS("Importación de estudios completada."))
        self.stdout.write(f"  ➕ Nuevos: {creados}")
        self.stdout.write(f"  ♻️ Actualizados: {actualizados}")
        self.stdout.write(f"  ⏭️ Sin cambios: {omitidos}")

        if errores:
            self.stdout.write(self.style.WARNING("Advertencias/errores:"))
            for error in errores:
                self.stdout.write(f"   - {error}")

