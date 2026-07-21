"""
Asigna tipo de tubo a todos los TipoExamen según reglas clínicas.

Uso:
  python manage.py asignar_tubos_examenes
  python manage.py asignar_tubos_examenes --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.models import TipoExamen
from laboratorio.models_catalog import TipoContenedor
from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, tubo_codigo_para_examen


class Command(BaseCommand):
    help = "Asigna tipo_contenedor a todos los exámenes del catálogo LIMS."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        with transaction.atomic():
            for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
                TipoContenedor.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "color": color,
                        "aditivo": aditivo,
                        "activo": True,
                        "descripcion": "",
                    },
                )
            by_codigo = {tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)}
            updated = 0
            skipped = 0
            for ex in TipoExamen.objects.select_related("tipo_muestra_requerida").iterator():
                muestra = ex.tipo_muestra_requerida.codigo if ex.tipo_muestra_requerida_id else None
                tubo = tubo_codigo_para_examen(ex.codigo, muestra)
                tc = by_codigo.get(tubo)
                if tc is None:
                    self.stdout.write(self.style.WARNING(f"  Sin contenedor {tubo} para {ex.codigo}"))
                    skipped += 1
                    continue
                if ex.tipo_contenedor_id == tc.pk:
                    skipped += 1
                    continue
                self.stdout.write(f"  {ex.codigo}: → {tubo}")
                if not dry_run:
                    TipoExamen.objects.filter(pk=ex.pk).update(tipo_contenedor_id=tc.pk)
                updated += 1
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING(f"Dry-run: {updated} cambiarían, {skipped} ok/omitidos."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Actualizados: {updated}. Sin cambio: {skipped}."))
