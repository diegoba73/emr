"""
Seed de materiales de pedido (TipoMuestra, TipoExamen, PanelExamen)
y extensión de catálogos de microbiología.

Uso:
    python manage.py seed_materiales_pedido
    python manage.py seed_materiales_pedido --dry-run
    python manage.py seed_materiales_pedido --solo-nuevos
    python manage.py seed_materiales_pedido --solo-nuevos --dry-run

--solo-nuevos: solo crea códigos ausentes; no actualiza ni desactiva existentes
(recomendado en producción con órdenes vivas).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.materiales_pedido_catalogo import (
    todas_muestras_clinicas,
    todos_examenes_materiales,
    todos_paneles_materiales,
)
from laboratorio.micro_catalogos_seed import seed_catalogos_microbiologia
from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import TipoContenedor
from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, tubo_codigo_para_examen


class Command(BaseCommand):
    help = (
        "Carga materiales de pedido (clínico + micro). "
        "Con --solo-nuevos no muta filas ya existentes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sin escribir en base de datos.",
        )
        parser.add_argument(
            "--solo-nuevos",
            action="store_true",
            help=(
                "Solo crea códigos que faltan. No actualiza nombre/tubo/"
                "requiere_muestra ni desactiva catálogo micro existente."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        solo_nuevos = options["solo_nuevos"]
        self.stats = {
            "contenedores_creados": 0,
            "contenedores_omitidos": 0,
            "muestras_creadas": 0,
            "muestras_omitidas": 0,
            "examenes_creados": 0,
            "examenes_omitidos": 0,
            "paneles_creados": 0,
            "paneles_omitidos": 0,
        }

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se guardarán cambios."))
        if solo_nuevos:
            self.stdout.write(
                self.style.WARNING(
                    "Modo --solo-nuevos: no se actualizan ni desactivan existentes."
                )
            )

        with transaction.atomic():
            self._ensure_contenedores(dry_run=dry_run, solo_nuevos=solo_nuevos)
            muestras = self._ensure_muestras(dry_run=dry_run, solo_nuevos=solo_nuevos)
            examenes_map = self._ensure_examenes(
                muestras, dry_run=dry_run, solo_nuevos=solo_nuevos
            )
            self._ensure_paneles(
                examenes_map, dry_run=dry_run, solo_nuevos=solo_nuevos
            )
            if not dry_run:
                stats = seed_catalogos_microbiologia(
                    update_existing=not solo_nuevos,
                    deactivate_missing=not solo_nuevos,
                )
                self.stdout.write(
                    f"  Micro: cultivos +{stats['cultivos_creados']}/"
                    f"~{stats['cultivos_actualizados']}"
                    f"/-{stats.get('cultivos_desactivados', 0)}, "
                    f"muestras +{stats['muestras_creadas']}/"
                    f"~{stats['muestras_actualizadas']}"
                )
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            "Resumen: "
            f"contenedores +{self.stats['contenedores_creados']}/"
            f"skip {self.stats['contenedores_omitidos']}; "
            f"muestras +{self.stats['muestras_creadas']}/"
            f"skip {self.stats['muestras_omitidas']}; "
            f"examenes +{self.stats['examenes_creados']}/"
            f"skip {self.stats['examenes_omitidos']}; "
            f"paneles +{self.stats['paneles_creados']}/"
            f"skip {self.stats['paneles_omitidos']}"
        )
        self.stdout.write(self.style.SUCCESS("Materiales de pedido cargados correctamente."))

    def _ensure_contenedores(self, *, dry_run: bool, solo_nuevos: bool) -> None:
        for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
            defaults = {
                "nombre": nombre,
                "color": color,
                "aditivo": aditivo,
                "activo": True,
            }
            existing = TipoContenedor.objects.filter(codigo=codigo).first()
            if existing is not None:
                self.stats["contenedores_omitidos"] += 1
                if not solo_nuevos and not dry_run:
                    for k, v in defaults.items():
                        setattr(existing, k, v)
                    existing.save()
                    self.stdout.write(f"  Contenedor {codigo}: actualizado")
                continue

            self.stats["contenedores_creados"] += 1
            self.stdout.write(f"  Contenedor {codigo}: crear")
            if not dry_run:
                TipoContenedor.objects.create(codigo=codigo, **defaults)

    def _ensure_muestras(
        self, *, dry_run: bool, solo_nuevos: bool
    ) -> dict[str, TipoMuestra]:
        out: dict[str, TipoMuestra] = {}
        for codigo, data in todas_muestras_clinicas().items():
            defaults = {**data, "activo": True}
            existing = TipoMuestra.objects.filter(codigo=codigo).first()
            if existing is not None:
                self.stats["muestras_omitidas"] += 1
                if not solo_nuevos and not dry_run:
                    for k, v in defaults.items():
                        setattr(existing, k, v)
                    existing.save()
                    self.stdout.write(f"  Muestra {codigo}: actualizado")
                out[codigo] = existing
                continue

            self.stats["muestras_creadas"] += 1
            self.stdout.write(f"  Muestra {codigo}: crear")
            if dry_run:
                # Placeholder no persistido; paneles/exámenes dry-run no lo necesitan
                # como FK real si solo reportamos.
                out[codigo] = TipoMuestra(codigo=codigo, **defaults)
            else:
                out[codigo] = TipoMuestra.objects.create(codigo=codigo, **defaults)

        if "MATERIA_FECAL" not in out:
            existing = TipoMuestra.objects.filter(codigo="MATERIA_FECAL").first()
            if existing is not None:
                out["MATERIA_FECAL"] = existing
            else:
                defaults = {
                    "nombre": "Materia fecal",
                    "color_tubo": "Frasco",
                    "activo": True,
                }
                self.stats["muestras_creadas"] += 1
                self.stdout.write("  Muestra MATERIA_FECAL: crear")
                if dry_run:
                    out["MATERIA_FECAL"] = TipoMuestra(codigo="MATERIA_FECAL", **defaults)
                else:
                    out["MATERIA_FECAL"] = TipoMuestra.objects.create(
                        codigo="MATERIA_FECAL", **defaults
                    )
        return out

    def _ensure_examenes(
        self,
        muestras: dict[str, TipoMuestra],
        *,
        dry_run: bool,
        solo_nuevos: bool,
    ) -> dict[str, TipoExamen]:
        out: dict[str, TipoExamen] = {}
        contenedores = {
            tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)
        }
        for item in todos_examenes_materiales():
            codigo = item.codigo
            existing = TipoExamen.objects.filter(codigo=codigo).first()
            if existing is not None:
                self.stats["examenes_omitidos"] += 1
                out[codigo] = existing
                if not solo_nuevos and not dry_run:
                    muestra = self._resolve_muestra(muestras, item.muestra, dry_run)
                    tubo_codigo = tubo_codigo_para_examen(codigo, item.muestra)
                    tubo = contenedores.get(tubo_codigo) if tubo_codigo else None
                    existing.nombre = item.nombre
                    existing.tipo_muestra_requerida = muestra
                    existing.tipo_resultado = item.tipo_resultado
                    existing.abreviatura = item.abreviatura or ""
                    existing.unidad_default = item.unidad_default or ""
                    existing.activo = True
                    existing.tipo_contenedor = tubo
                    existing.requiere_muestra = True
                    existing.save()
                    self.stdout.write(f"  Examen {codigo}: actualizado")
                continue

            muestra = self._resolve_muestra(muestras, item.muestra, dry_run)
            tubo_codigo = tubo_codigo_para_examen(codigo, item.muestra)
            tubo = contenedores.get(tubo_codigo) if tubo_codigo else None
            defaults = {
                "nombre": item.nombre,
                "tipo_muestra_requerida": muestra if getattr(muestra, "pk", None) else None,
                "tipo_resultado": item.tipo_resultado,
                "abreviatura": item.abreviatura or "",
                "unidad_default": item.unidad_default or "",
                "activo": True,
                "tipo_contenedor": tubo,
                "requiere_muestra": True,
                "precio": 0,
            }
            self.stats["examenes_creados"] += 1
            self.stdout.write(f"  Examen {codigo}: crear ({tubo_codigo or 'sin tubo'})")
            if dry_run:
                out[codigo] = TipoExamen(codigo=codigo, **defaults)
            else:
                # Si la muestra es placeholder dry-run no llega aquí.
                if defaults["tipo_muestra_requerida"] is None:
                    muestra_db = TipoMuestra.objects.get(codigo=item.muestra)
                    defaults["tipo_muestra_requerida"] = muestra_db
                out[codigo] = TipoExamen.objects.create(codigo=codigo, **defaults)
        return out

    def _resolve_muestra(
        self, muestras: dict[str, TipoMuestra], codigo: str, dry_run: bool
    ) -> TipoMuestra:
        muestra = muestras.get(codigo)
        if muestra is not None:
            return muestra
        existing = TipoMuestra.objects.filter(codigo=codigo).first()
        if existing is not None:
            muestras[codigo] = existing
            return existing
        defaults = {
            "nombre": codigo,
            "color_tubo": "Transparente",
            "activo": True,
        }
        self.stats["muestras_creadas"] += 1
        self.stdout.write(f"  Muestra {codigo}: crear (ref examen)")
        if dry_run:
            obj = TipoMuestra(codigo=codigo, **defaults)
        else:
            obj = TipoMuestra.objects.create(codigo=codigo, **defaults)
        muestras[codigo] = obj
        return obj

    def _ensure_paneles(
        self,
        examenes_map: dict[str, TipoExamen],
        *,
        dry_run: bool,
        solo_nuevos: bool,
    ) -> None:
        for panel_def in todos_paneles_materiales():
            componentes = [
                examenes_map[c]
                for c in panel_def.componentes
                if c in examenes_map and getattr(examenes_map[c], "pk", None)
            ]
            missing = set(panel_def.componentes) - set(examenes_map)
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Panel {panel_def.codigo}: faltan componentes {missing}"
                    )
                )

            existing = PanelExamen.objects.filter(codigo=panel_def.codigo).first()
            if existing is not None:
                self.stats["paneles_omitidos"] += 1
                if solo_nuevos:
                    continue
                if not dry_run:
                    existing.nombre = panel_def.nombre
                    existing.activo = True
                    existing.save()
                    # Solo en modo full se reemplaza M2M (no en --solo-nuevos).
                    if componentes:
                        existing.tipos_examen.set(componentes)
                    self.stdout.write(
                        f"  Panel {panel_def.codigo} ({len(componentes)} ítems): actualizado"
                    )
                continue

            self.stats["paneles_creados"] += 1
            self.stdout.write(
                f"  Panel {panel_def.codigo}: crear ({len(componentes)} ítems)"
            )
            if dry_run:
                continue
            panel = PanelExamen.objects.create(
                codigo=panel_def.codigo,
                nombre=panel_def.nombre,
                activo=True,
            )
            if componentes:
                panel.tipos_examen.set(componentes)
