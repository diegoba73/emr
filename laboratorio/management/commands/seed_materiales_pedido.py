"""
Seed aditivo de materiales de pedido (TipoMuestra, TipoExamen, PanelExamen)
y extensión de catálogos de microbiología.

Uso:
    python manage.py seed_materiales_pedido
    python manage.py seed_materiales_pedido --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.materiales_pedido_catalogo import (
    CONTENEDOR_ESTERIL,
    todas_muestras_clinicas,
    todos_examenes_materiales,
    todos_paneles_materiales,
)
from laboratorio.micro_catalogos_seed import seed_catalogos_microbiologia
from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import TipoContenedor
from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, tubo_codigo_para_examen


class Command(BaseCommand):
    help = "Carga materiales de pedido (clínico + micro) de forma idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sin escribir en base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se guardarán cambios."))

        with transaction.atomic():
            self._ensure_contenedores(dry_run)
            muestras = self._ensure_muestras(dry_run)
            examenes_map = self._ensure_examenes(muestras, dry_run)
            self._ensure_paneles(examenes_map, dry_run)
            if not dry_run:
                stats = seed_catalogos_microbiologia(update_existing=True)
                self.stdout.write(
                    f"  Micro: cultivos +{stats['cultivos_creados']}/"
                    f"~{stats['cultivos_actualizados']}, "
                    f"muestras +{stats['muestras_creadas']}/"
                    f"~{stats['muestras_actualizadas']}"
                )
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Materiales de pedido cargados correctamente."))

    def _ensure_contenedores(self, dry_run: bool) -> None:
        for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
            defaults = {
                "nombre": nombre,
                "color": color,
                "aditivo": aditivo,
                "activo": True,
            }
            if dry_run:
                TipoContenedor.objects.get_or_create(codigo=codigo, defaults=defaults)
            else:
                obj, created = TipoContenedor.objects.update_or_create(
                    codigo=codigo, defaults=defaults
                )
                if created or codigo == CONTENEDOR_ESTERIL:
                    tag = "creado" if created else "actualizado"
                    self.stdout.write(f"  Contenedor {codigo}: {tag}")

    def _ensure_muestras(self, dry_run: bool) -> dict[str, TipoMuestra]:
        out: dict[str, TipoMuestra] = {}
        for codigo, data in todas_muestras_clinicas().items():
            defaults = {**data, "activo": True}
            if dry_run:
                obj, _ = TipoMuestra.objects.get_or_create(
                    codigo=codigo, defaults=defaults
                )
            else:
                obj, created = TipoMuestra.objects.update_or_create(
                    codigo=codigo, defaults=defaults
                )
                tag = "creado" if created else "actualizado"
                self.stdout.write(f"  Muestra {codigo}: {tag}")
            out[codigo] = obj
        # Asegurar MATERIA_FECAL legacy si falta
        if "MATERIA_FECAL" not in out:
            obj, _ = TipoMuestra.objects.get_or_create(
                codigo="MATERIA_FECAL",
                defaults={
                    "nombre": "Materia fecal",
                    "color_tubo": "Frasco",
                    "activo": True,
                },
            )
            out["MATERIA_FECAL"] = obj
        return out

    def _ensure_examenes(
        self, muestras: dict[str, TipoMuestra], dry_run: bool
    ) -> dict[str, TipoExamen]:
        out: dict[str, TipoExamen] = {}
        contenedores = {
            tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)
        }
        for item in todos_examenes_materiales():
            codigo = item.codigo
            muestra = muestras.get(item.muestra)
            if muestra is None:
                muestra, _ = TipoMuestra.objects.get_or_create(
                    codigo=item.muestra,
                    defaults={
                        "nombre": item.muestra,
                        "color_tubo": "Transparente",
                        "activo": True,
                    },
                )
                muestras[item.muestra] = muestra
            tubo_codigo = tubo_codigo_para_examen(codigo, item.muestra)
            tubo = contenedores.get(tubo_codigo) if tubo_codigo else None
            defaults = {
                "nombre": item.nombre,
                "tipo_muestra_requerida": muestra,
                "tipo_resultado": item.tipo_resultado,
                "abreviatura": item.abreviatura or "",
                "unidad_default": item.unidad_default or "",
                "activo": True,
                "tipo_contenedor": tubo,
                "requiere_muestra": True,
                "precio": 0,
            }
            if dry_run:
                obj, _ = TipoExamen.objects.get_or_create(
                    codigo=codigo, defaults=defaults
                )
            else:
                obj, created = TipoExamen.objects.update_or_create(
                    codigo=codigo, defaults=defaults
                )
                if created:
                    self.stdout.write(
                        f"  Examen {codigo}: creado ({tubo_codigo or 'sin tubo'})"
                    )
            out[codigo] = obj
        return out

    def _ensure_paneles(
        self, examenes_map: dict[str, TipoExamen], dry_run: bool
    ) -> None:
        for panel_def in todos_paneles_materiales():
            componentes = [
                examenes_map[c]
                for c in panel_def.componentes
                if c in examenes_map
            ]
            if len(componentes) != len(panel_def.componentes):
                missing = set(panel_def.componentes) - set(examenes_map)
                self.stdout.write(
                    self.style.WARNING(
                        f"  Panel {panel_def.codigo}: faltan componentes {missing}"
                    )
                )
            defaults = {"nombre": panel_def.nombre, "activo": True}
            if dry_run:
                panel, _ = PanelExamen.objects.get_or_create(
                    codigo=panel_def.codigo, defaults=defaults
                )
                panel.tipos_examen.set(componentes)
            else:
                panel, created = PanelExamen.objects.update_or_create(
                    codigo=panel_def.codigo, defaults=defaults
                )
                panel.tipos_examen.set(componentes)
                tag = "creado" if created else "actualizado"
                self.stdout.write(
                    f"  Panel {panel_def.codigo} ({len(componentes)} ítems): {tag}"
                )
