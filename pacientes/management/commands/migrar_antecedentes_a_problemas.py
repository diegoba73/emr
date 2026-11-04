"""
Propone / crea ProblemaClinico principal desde antecedentes_personales.

Uso:
  python manage.py migrar_antecedentes_a_problemas --dry-run
  python manage.py migrar_antecedentes_a_problemas --aplicar
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from pacientes.models import Paciente, ProblemaClinico
from pacientes.problemas import crear_problema


class Command(BaseCommand):
    help = (
        "Migra antecedentes_personales no vacíos a ProblemaClinico principal "
        "cuando el paciente aún no tiene problemas activos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo lista candidatos (default si no se pasa --aplicar).",
        )
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Crea los problemas principales.",
        )

    def handle(self, *args, **options):
        aplicar = bool(options.get("aplicar"))
        qs = (
            Paciente.objects.exclude(antecedentes_personales__isnull=True)
            .exclude(antecedentes_personales="")
            .order_by("id")
        )
        creados = 0
        omitidos = 0
        for pac in qs.iterator():
            ant = " ".join((pac.antecedentes_personales or "").split()).strip()
            if not ant:
                continue
            ya = ProblemaClinico.objects.filter(
                paciente_id=pac.pk, estado=ProblemaClinico.ESTADO_ACTIVO
            ).exists()
            if ya:
                omitidos += 1
                continue
            self.stdout.write(
                f"paciente={pac.pk} dni={pac.dni}: «{ant[:120]}»"
            )
            if aplicar:
                crear_problema(
                    pac,
                    texto=ant[:500],
                    es_principal=True,
                    notas="Migrado desde antecedentes_personales",
                )
                creados += 1
        modo = "APLICADO" if aplicar else "DRY-RUN"
        self.stdout.write(
            self.style.SUCCESS(
                f"{modo}: creados={creados} omitidos_con_problemas={omitidos}"
            )
        )
        if not aplicar:
            self.stdout.write("Reejecutá con --aplicar para persistir.")
