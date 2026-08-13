"""Pasa a mayúsculas los campos demográficos de todos los pacientes."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from pacientes.models import Paciente
from pacientes.texto import CAMPOS_PACIENTE_MAYUSCULAS, aplicar_mayusculas_paciente


class Command(BaseCommand):
    help = (
        "Normaliza nombre, apellido, dirección, obra social y nº afiliado "
        "a mayúsculas (strip). No toca resultados de laboratorio ni observaciones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Cuenta filas a cambiar sin escribir.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Tamaño de lote para commits (default 500).",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        batch_size = max(1, options["batch_size"])
        total = Paciente.objects.count()
        changed = 0
        scanned = 0
        pending: list[tuple[int, dict[str, str]]] = []

        self.stdout.write(f"Pacientes en BD: {total}")
        if dry:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se escribe."))

        qs = Paciente.objects.only("id", *CAMPOS_PACIENTE_MAYUSCULAS).order_by("id")

        def flush(rows: list[tuple[int, dict[str, str]]]) -> None:
            if not rows or dry:
                return
            with transaction.atomic():
                for pk, updates in rows:
                    Paciente.objects.filter(pk=pk).update(**updates)

        for obj in qs.iterator(chunk_size=batch_size):
            scanned += 1
            dirty = aplicar_mayusculas_paciente(obj)
            if not dirty:
                continue
            changed += 1
            updates = {f: getattr(obj, f) for f in dirty}
            if dry:
                continue
            pending.append((obj.pk, updates))
            if len(pending) >= batch_size:
                flush(pending)
                pending.clear()

        flush(pending)

        verb = "cambiarían" if dry else "actualizados"
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo. Escaneados: {scanned}. {verb.capitalize()}: {changed}."
            )
        )
