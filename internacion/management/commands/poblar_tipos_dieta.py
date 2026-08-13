"""Carga idempotente de tipos terapéuticos de dieta para internación."""
from django.core.management.base import BaseCommand

from internacion.models import TipoDieta

TIPOS_DIETA = [
    ("General", ""),
    ("Hiposódica", "Para hipertensión / restricción de sodio"),
    ("Diabética", ""),
    ("Hipotónica", ""),
    ("Hipocalórica", ""),
    ("Blanda", ""),
    ("Líquida", ""),
    ("Licuada", ""),
    ("Nefroprotectora", ""),
    ("Hepática", ""),
    ("Sin residuos", ""),
    ("Nada por boca", ""),
]


class Command(BaseCommand):
    help = "Crea los tipos de dieta de internación si no existen"

    def handle(self, *args, **options):
        creados = 0
        existentes = 0
        for nombre, descripcion in TIPOS_DIETA:
            defaults = {"activo": True}
            if descripcion:
                defaults["descripcion"] = descripcion
            _, created = TipoDieta.objects.get_or_create(
                nombre=nombre,
                defaults=defaults,
            )
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f"Creado tipo de dieta: {nombre}"))
            else:
                existentes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tipos de dieta: {creados} creados, {existentes} ya existían "
                f"({len(TIPOS_DIETA)} en total)."
            )
        )
