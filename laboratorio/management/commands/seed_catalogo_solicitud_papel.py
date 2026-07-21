"""
Carga idempotente del catálogo LIMS según formulario «Solicitud de análisis» (papel).

Uso:
    python manage.py seed_catalogo_solicitud_papel
    python manage.py seed_catalogo_solicitud_papel --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.catalogo_entrada_default import entrada_defaults_dict
from laboratorio.catalogo_referencias_clinicas import REFERENCIAS_LEGACY, REFERENCIAS_POR_CODIGO
from laboratorio.catalogo_solicitud_papel import (
    EXAMENES,
    EXAMENES_SUELTOS_PDF,
    LEGACY_CODIGOS_DESACTIVAR,
    MUESTRAS,
    PANELES,
)
from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import TipoContenedor
from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, tubo_codigo_para_examen


class Command(BaseCommand):
    help = "Carga paneles y exámenes del formulario de solicitud de análisis en papel."

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
            muestras = self._ensure_muestras(dry_run)
            self._ensure_contenedores(dry_run)
            examenes_map = self._ensure_examenes(muestras, dry_run)
            self._deactivate_legacy(examenes_map, dry_run)
            self._ensure_paneles(examenes_map, dry_run)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Catálogo de solicitud en papel cargado correctamente."))
        self._print_resumen()

    def _ensure_muestras(self, dry_run: bool) -> dict[str, TipoMuestra]:
        out: dict[str, TipoMuestra] = {}
        for codigo, data in MUESTRAS.items():
            if dry_run:
                obj, _ = TipoMuestra.objects.get_or_create(
                    codigo=codigo,
                    defaults={**data, "activo": True},
                )
            else:
                obj, created = TipoMuestra.objects.update_or_create(
                    codigo=codigo,
                    defaults={**data, "activo": True},
                )
                tag = "creado" if created else "actualizado"
                self.stdout.write(f"  Muestra {codigo}: {tag}")
            out[codigo] = obj
        return out

    def _referencia_defaults(self, codigo: str) -> dict:
        ref = REFERENCIAS_POR_CODIGO.get(codigo) or REFERENCIAS_LEGACY.get(codigo) or {}
        out: dict = {}
        if ref.get("metodo"):
            out["metodo"] = ref["metodo"]
        if ref.get("unidad_default"):
            out["unidad_default"] = ref["unidad_default"]
        if ref.get("rango_referencia_texto"):
            out["rango_referencia_texto"] = ref["rango_referencia_texto"]
        for field in (
            "rango_min",
            "rango_max",
            "valor_critico_min",
            "valor_critico_max",
        ):
            if field in ref:
                out[field] = ref[field]
        out.update(entrada_defaults_dict(codigo))
        return out

    def _ensure_contenedores(self, dry_run: bool) -> None:
        for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
            if dry_run:
                TipoContenedor.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "color": color,
                        "aditivo": aditivo,
                        "activo": True,
                    },
                )
            else:
                obj, created = TipoContenedor.objects.update_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "color": color,
                        "aditivo": aditivo,
                        "activo": True,
                    },
                )
                tag = "creado" if created else "actualizado"
                self.stdout.write(f"  Contenedor {codigo}: {tag}")

    def _ensure_examenes(
        self, muestras: dict[str, TipoMuestra], dry_run: bool
    ) -> dict[str, TipoExamen]:
        out: dict[str, TipoExamen] = {}
        contenedores = {tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)}
        for item in EXAMENES:
            codigo = item["codigo"]
            muestra = muestras[item["muestra"]]
            tubo_codigo = tubo_codigo_para_examen(codigo, item.get("muestra"))
            tubo = contenedores.get(tubo_codigo)
            defaults = {
                "nombre": item["nombre"],
                "tipo_muestra_requerida": muestra,
                "tipo_resultado": item.get("tipo_resultado", "NUMERICO"),
                "abreviatura": item.get("abreviatura", "") or "",
                "activo": True,
                **self._referencia_defaults(codigo),
            }
            if tubo is not None:
                defaults["tipo_contenedor"] = tubo
            if dry_run:
                obj, _ = TipoExamen.objects.get_or_create(codigo=codigo, defaults=defaults)
            else:
                obj, created = TipoExamen.objects.update_or_create(
                    codigo=codigo,
                    defaults=defaults,
                )
                if created:
                    self.stdout.write(f"  Examen {codigo}: creado ({tubo_codigo})")
                elif tubo is not None and obj.tipo_contenedor_id != tubo.pk:
                    obj.tipo_contenedor = tubo
                    obj.save(update_fields=["tipo_contenedor"])
                    self.stdout.write(f"  Examen {codigo}: tubo → {tubo_codigo}")
            out[codigo] = obj
        return out

    def _deactivate_legacy(
        self, examenes_map: dict[str, TipoExamen], dry_run: bool
    ) -> None:
        for codigo in LEGACY_CODIGOS_DESACTIVAR:
            qs = TipoExamen.objects.filter(codigo=codigo, activo=True)
            if not qs.exists():
                continue
            if not dry_run:
                qs.update(activo=False)
            self.stdout.write(
                self.style.WARNING(f"  Legacy {codigo} desactivado (reemplazado por catálogo nuevo)")
            )

    def _ensure_paneles(
        self, examenes_map: dict[str, TipoExamen], dry_run: bool
    ) -> None:
        for panel_def in PANELES:
            codigo = panel_def["codigo"]
            componentes = [
                examenes_map[c] for c in panel_def["componentes"]
            ]
            if dry_run:
                panel, _ = PanelExamen.objects.get_or_create(
                    codigo=codigo,
                    defaults={"nombre": panel_def["nombre"], "activo": True},
                )
                panel.tipos_examen.set(componentes)
            else:
                panel, created = PanelExamen.objects.update_or_create(
                    codigo=codigo,
                    defaults={"nombre": panel_def["nombre"], "activo": True},
                )
                panel.tipos_examen.set(componentes)
                tag = "creado" if created else "actualizado"
                self.stdout.write(
                    f"  Panel {codigo} ({len(componentes)} ítems): {tag}"
                )

    def _print_resumen(self) -> None:
        panel_codes = {p["codigo"] for p in PANELES}
        in_panel = {
            c for p in PANELES for c in p["componentes"]
        }
        sueltos_ok = set(EXAMENES_SUELTOS_PDF) - in_panel
        self.stdout.write(
            f"\nResumen: {len(EXAMENES)} exámenes, {len(PANELES)} paneles, "
            f"{len(sueltos_ok)} exámenes sueltos en el formulario."
        )
        self.stdout.write(f"Paneles: {', '.join(sorted(panel_codes))}")
