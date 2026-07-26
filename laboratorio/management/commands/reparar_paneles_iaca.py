"""
Repara paneles tras sync IACA: componentes activos, M2M, desactiva productos-panel IACA.

Uso:
  python manage.py reparar_paneles_iaca
  python manage.py reparar_paneles_iaca --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.catalogo_entrada_default import entrada_defaults_dict
from laboratorio.catalogo_referencias_clinicas import REFERENCIAS_LEGACY, REFERENCIAS_POR_CODIGO
from laboratorio.catalogo_solicitud_papel import EXAMENES, MUESTRAS, PANELES
from laboratorio.iaca_compat import (
    IACA_PRODUCTOS_COMPUESTOS_EXTRA,
    IACA_PRODUCTO_A_PANEL,
)
from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import TipoContenedor
from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, tubo_codigo_para_examen


class Command(BaseCommand):
    help = "Repara paneles LIMS y desactiva productos IACA que son paneles."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("dry-run: sin persistir"))

        stats = {
            "muestras": 0,
            "contenedores": 0,
            "examenes_ok": 0,
            "examenes_creados": 0,
            "examenes_reactivados": 0,
            "paneles": 0,
            "productos_desactivados": 0,
        }

        with transaction.atomic():
            muestras = self._ensure_muestras(dry, stats)
            self._ensure_contenedores(dry, stats)
            examenes = self._ensure_examenes(muestras, dry, stats)
            self._ensure_paneles(examenes, dry, stats)
            self._deactivate_iaca_panel_products(dry, stats)
            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Reparación de paneles finalizada"))
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")
        self._verify()

    def _ensure_muestras(self, dry, stats):
        out = {}
        for codigo, data in MUESTRAS.items():
            obj, created = TipoMuestra.objects.get_or_create(
                codigo=codigo,
                defaults={**data, "activo": True},
            )
            if not dry and not obj.activo:
                obj.activo = True
                obj.save(update_fields=["activo"])
            if created:
                stats["muestras"] += 1
            out[codigo] = obj
        return out

    def _ensure_contenedores(self, dry, stats):
        for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
            _, created = TipoContenedor.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "color": color,
                    "aditivo": aditivo,
                    "activo": True,
                },
            )
            if created:
                stats["contenedores"] += 1

    def _referencia_defaults(self, codigo: str) -> dict:
        ref = REFERENCIAS_POR_CODIGO.get(codigo) or REFERENCIAS_LEGACY.get(codigo) or {}
        out: dict = {}
        if ref.get("metodo"):
            out["metodo"] = ref["metodo"]
        if ref.get("unidad_default"):
            out["unidad_default"] = ref["unidad_default"]
        if ref.get("rango_referencia_texto"):
            out["rango_referencia_texto"] = ref["rango_referencia_texto"]
        for field in ("rango_min", "rango_max", "valor_critico_min", "valor_critico_max"):
            if field in ref:
                out[field] = ref[field]
        out.update(entrada_defaults_dict(codigo))
        return out

    def _ensure_examenes(self, muestras, dry, stats):
        out = {}
        contenedores = {tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)}
        for item in EXAMENES:
            codigo = item["codigo"]
            muestra = muestras[item["muestra"]]
            tubo = contenedores.get(tubo_codigo_para_examen(codigo, item.get("muestra")))
            defaults = {
                "nombre": item["nombre"],
                "tipo_muestra_requerida": muestra,
                "tipo_resultado": item.get("tipo_resultado", "NUMERICO"),
                "abreviatura": item.get("abreviatura", "") or "",
                "activo": True,
                "requiere_muestra": True,
                **self._referencia_defaults(codigo),
            }
            if tubo is not None:
                defaults["tipo_contenedor"] = tubo

            existing = TipoExamen.objects.filter(codigo=codigo).first()
            if existing is None:
                if dry:
                    stats["examenes_creados"] += 1
                    continue
                obj = TipoExamen.objects.create(codigo=codigo, **defaults)
                stats["examenes_creados"] += 1
                self.stdout.write(f"  + examen operativo {codigo}")
            else:
                obj = existing
                changed = []
                if not obj.activo:
                    obj.activo = True
                    changed.append("activo")
                    stats["examenes_reactivados"] += 1
                # No pisar nombre IACA si el código es compartido y ya es el producto IACA
                # distinto (p.ej. CL, TP, HTO, FAL, TG, TRANS, ALB…). Solo forzar nombre
                # operativo cuando el registro estaba inactivo o es código operativo puro.
                if obj.nombre != item["nombre"] and (
                    not existing.activo or codigo in {"LEUCO", "CREATI", "HGB", "PLAQ", "HEMATIES"}
                    or codigo.startswith("ORI_") or codigo.startswith("ELP_")
                    or codigo.startswith("NEUT_") or codigo in {
                        "VCM", "CHCM", "RDW", "EOS", "BAS", "LINF", "MONO",
                        "PP", "INR", "CF", "FERR", "SAT_FE", "BIL_T", "BIL_D",
                        "NA", "K", "COL_TOT", "HDL", "LDL", "COL_NO_LDL",
                        "GOT", "GPT", "NA_U", "K_U", "CL_U", "CREA_U", "DIUR",
                        "CLEAR_CREA", "MICROALB", "AU", "P", "PROT_T", "VSG",
                        "PCR_US", "AMIL", "LIP", "CPK", "CPK_MB", "DDIM", "B12",
                        "VITD", "PSA", "CA_ION", "EAB_ART", "EAB_VEN", "LACT",
                        "TROP_I", "TROP_US", "PROBNP", "PROT_U_24", "PROT_U_AZ",
                    }
                ):
                    obj.nombre = item["nombre"]
                    changed.append("nombre")
                if obj.tipo_muestra_requerida_id != muestra.id:
                    obj.tipo_muestra_requerida = muestra
                    changed.append("tipo_muestra_requerida")
                if tubo and obj.tipo_contenedor_id != tubo.id:
                    obj.tipo_contenedor = tubo
                    changed.append("tipo_contenedor")
                for k, v in self._referencia_defaults(codigo).items():
                    if getattr(obj, k) in (None, "", 0) and v not in (None, ""):
                        setattr(obj, k, v)
                        changed.append(k)
                if changed and not dry:
                    obj.save()
                    self.stdout.write(f"  ~ examen {codigo}: {', '.join(changed)}")
                stats["examenes_ok"] += 1
            out[codigo] = obj
        return out

    def _ensure_paneles(self, examenes, dry, stats):
        for panel_def in PANELES:
            codigo = panel_def["codigo"]
            missing = [c for c in panel_def["componentes"] if c not in examenes]
            if missing:
                raise RuntimeError(f"Panel {codigo}: faltan componentes {missing}")
            componentes = [examenes[c] for c in panel_def["componentes"]]
            panel, created = PanelExamen.objects.update_or_create(
                codigo=codigo,
                defaults={"nombre": panel_def["nombre"], "activo": True},
            )
            if not dry:
                panel.tipos_examen.set(componentes)
            stats["paneles"] += 1
            tag = "creado" if created else "actualizado"
            self.stdout.write(f"  panel {codigo}: {tag} ({len(componentes)} componentes)")

    def _deactivate_iaca_panel_products(self, dry, stats):
        codes = set(IACA_PRODUCTO_A_PANEL) | set(IACA_PRODUCTOS_COMPUESTOS_EXTRA)
        qs = TipoExamen.objects.filter(codigo__in=codes, activo=True)
        n = qs.count()
        stats["productos_desactivados"] = n
        if n and not dry:
            qs.update(activo=False)
            self.stdout.write(self.style.WARNING(f"  desactivados productos-panel IACA: {n}"))
            for code, pan in sorted(IACA_PRODUCTO_A_PANEL.items()):
                self.stdout.write(f"    {code} → panel {pan}")

    def _verify(self):
        errors = []
        for panel_def in PANELES:
            panel = PanelExamen.objects.filter(codigo=panel_def["codigo"], activo=True).first()
            if not panel:
                errors.append(f"falta panel {panel_def['codigo']}")
                continue
            have = set(panel.tipos_examen.filter(activo=True).values_list("codigo", flat=True))
            need = set(panel_def["componentes"])
            if have != need:
                errors.append(
                    f"{panel_def['codigo']}: have={sorted(have)} need={sorted(need)}"
                )
        for code in IACA_PRODUCTO_A_PANEL:
            if TipoExamen.objects.filter(codigo=code, activo=True).exists():
                errors.append(f"producto IACA {code} sigue activo como TipoExamen")
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f"VERIFY FAIL: {e}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("VERIFY OK: paneles íntegros, sin productos-panel activos"))