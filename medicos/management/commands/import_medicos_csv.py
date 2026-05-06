import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from medicos.models import Medico


def normalizar_espacios(valor: str) -> str:
    if not valor:
        return ""
    return " ".join(valor.split()).strip()


def dividir_nombre_completo(valor: str) -> tuple[str, str]:
    valor = normalizar_espacios(valor.replace('"', ""))
    if not valor:
        return "", ""

    if "," in valor:
        apellido, nombre = valor.split(",", 1)
        return normalizar_espacios(apellido), normalizar_espacios(nombre)

    partes = valor.split()
    if len(partes) == 1:
        return partes[0], ""
    apellido = partes[0]
    nombre = " ".join(partes[1:])
    return normalizar_espacios(apellido), normalizar_espacios(nombre)


def normalizar_header(clave: str | None) -> str:
    if not clave:
        return ""
    return "".join(ch for ch in clave.lower() if ch.isalnum())


def obtener_columna(row: dict, clave: str) -> str | None:
    clave_normalizada = normalizar_header(clave)
    for columna, valor in row.items():
        if normalizar_header(columna) == clave_normalizada:
            return valor
    return None


class Command(BaseCommand):
    help = (
        "Importa médicos desde un archivo CSV con columnas 'matricula' y "
        "'apellido y nombre' (o 'apellido_nombre'). No crea usuarios."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Ruta absoluta o relativa al archivo CSV de médicos.",
        )
        parser.add_argument(
            "--encoding",
            default="latin-1",
            help="Encoding del archivo (por defecto latin-1).",
        )
        parser.add_argument(
            "--delimiter",
            default=",",
            help="Delimitador del CSV (por defecto ',').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué cambios se harían sin escribir en la base.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Sobrescribe nombre/apellido aun cuando ya existen datos.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"El archivo CSV no existe: {csv_path}")

        encoding = options["encoding"]
        delimiter = options["delimiter"]
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        created = 0
        updated = 0
        skipped = 0
        errores: list[str] = []

        with csv_path.open(newline="", encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            if not reader.fieldnames:
                raise CommandError("El archivo CSV no tiene encabezados.")

            headers_normalizados = {normalizar_header(col) for col in reader.fieldnames}
            if "matricula" not in headers_normalizados:
                raise CommandError("El CSV debe incluir una columna 'matricula'.")
            if "apellidoynombre" not in headers_normalizados and "apellidonombre" not in headers_normalizados:
                raise CommandError(
                    "El CSV debe incluir una columna 'apellido y nombre' o 'apellido_nombre'."
                )

            for indice, row in enumerate(reader, start=2):
                matricula = obtener_columna(row, "matricula")
                nombre_completo = (
                    obtener_columna(row, "apellido y nombre")
                    or obtener_columna(row, "apellido_nombre")
                )

                matricula = normalizar_espacios(str(matricula or ""))
                if not matricula:
                    errores.append(
                        f"Línea {indice}: sin matrícula, registro omitido."
                    )
                    skipped += 1
                    continue

                apellido, nombre = dividir_nombre_completo(nombre_completo or "")
                if not apellido and not nombre:
                    errores.append(
                        f"Línea {indice}: no se pudo obtener nombre/apellido para matrícula {matricula}."
                    )
                    skipped += 1
                    continue

                medico = Medico.objects.filter(matricula=matricula).first()
                if not medico:
                    if dry_run:
                        created += 1
                    else:
                        Medico.objects.create(
                            matricula=matricula,
                            apellido=apellido or None,
                            nombre=nombre or None,
                        )
                        created += 1
                    continue

                cambios_realizados = False
                campos_a_actualizar = []

                if apellido and (overwrite or not medico.apellido):
                    if medico.apellido != apellido:
                        cambios_realizados = True
                        campos_a_actualizar.append("apellido")
                        if not dry_run:
                            medico.apellido = apellido

                if nombre and (overwrite or not medico.nombre):
                    if medico.nombre != nombre:
                        cambios_realizados = True
                        campos_a_actualizar.append("nombre")
                        if not dry_run:
                            medico.nombre = nombre

                if cambios_realizados:
                    if dry_run:
                        updated += 1
                    else:
                        campos_a_actualizar.append("ultima_actualizacion")
                        medico.save(update_fields=list(set(campos_a_actualizar)))
                        updated += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS("Importación de médicos completada."))
        self.stdout.write(f"  ➕ Nuevos: {created}")
        self.stdout.write(f"  ♻️ Actualizados: {updated}")
        self.stdout.write(f"  ⏭️ Sin cambios: {skipped}")

        if errores:
            self.stdout.write(self.style.WARNING("Advertencias/errores:"))
            for error in errores:
                self.stdout.write(f"   - {error}")

