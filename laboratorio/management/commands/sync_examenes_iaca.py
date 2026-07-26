"""
Sincroniza TipoExamen / TipoMuestra con el CSV IACA (examenes_completos.csv).

- Códigos del CSV (IACA) son la fuente de verdad.
- Si un examen existente coincide por código o por nombre normalizado, se actualiza
  (sin duplicar).
- Material del CSV se crea/asocia como TipoMuestra.
- Exámenes de BD que no quedan en el catálogo CSV se desactivan (no se borran).

Uso:
    python manage.py sync_examenes_iaca examenes_completos.csv
    python manage.py sync_examenes_iaca examenes_completos.csv --dry-run
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from laboratorio.models import TipoExamen, TipoMuestra


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def norm_text(s: str) -> str:
    s = strip_accents((s or "").strip().lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def material_codigo(nombre: str) -> str:
    base = strip_accents((nombre or "").strip().upper())
    base = re.sub(r"[^A-Z0-9]+", "_", base).strip("_")
    if not base:
        base = "SIN_MATERIAL"
    return base[:64]


class Command(BaseCommand):
    help = "Sincroniza catálogo de exámenes con CSV IACA (códigos + materiales)."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Ruta al archivo examenes_completos.csv",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sin persistir cambios.",
        )
        parser.add_argument(
            "--keep-orphans-active",
            action="store_true",
            help="No desactivar exámenes de BD ausentes en el CSV.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.is_file():
            raise CommandError(f"No existe el CSV: {csv_path}")

        dry_run = options["dry_run"]
        keep_orphans = options["keep_orphans_active"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se guardarán cambios."))

        rows = self._load_csv(csv_path)
        self.stdout.write(
            f"CSV: {len(rows)} filas únicas por código "
            f"(dedupe por Codigo, se conserva mayor ID)."
        )

        stats = defaultdict(int)
        with transaction.atomic():
            muestras = self._ensure_muestras(rows, stats, dry_run)
            claimed = self._sync_examenes(rows, muestras, stats, dry_run)
            if not keep_orphans:
                self._deactivate_orphans(claimed, stats, dry_run)
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Sync IACA finalizado."))
        for k in sorted(stats):
            self.stdout.write(f"  {k}: {stats[k]}")
        self.stdout.write(
            f"  total_activos: {TipoExamen.objects.filter(activo=True).count()}"
        )
        self.stdout.write(
            f"  total_muestras_activas: {TipoMuestra.objects.filter(activo=True).count()}"
        )

    def _load_csv(self, csv_path: Path) -> list[dict]:
        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            raw = list(csv.DictReader(f))

        by_code: dict[str, dict] = {}
        skipped_empty = 0
        for r in raw:
            code = (r.get("Codigo") or "").strip().upper()
            nombre = (r.get("Examen") or "").strip()
            if not code or not nombre:
                skipped_empty += 1
                continue
            material = (r.get("Material") or "").strip() or "otro material"
            rid = int(r.get("ID") or 0)
            prev = by_code.get(code)
            if prev is None or rid > prev["_id"]:
                by_code[code] = {
                    "codigo": code,
                    "nombre": nombre,
                    "material": material,
                    "_id": rid,
                }

        if skipped_empty:
            self.stdout.write(
                self.style.WARNING(f"Filas omitidas (sin código/nombre): {skipped_empty}")
            )
        # Orden estable por ID IACA
        return sorted(by_code.values(), key=lambda x: x["_id"])

    def _ensure_muestras(self, rows, stats, dry_run: bool) -> dict[str, TipoMuestra]:
        """Mapa norm(material) -> TipoMuestra."""
        # Preferir nombre con acentos / más frecuente
        preferred: dict[str, str] = {}
        counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for r in rows:
            key = norm_text(r["material"])
            counts[key][r["material"]] += 1
        for key, variants in counts.items():
            preferred[key] = max(variants.items(), key=lambda kv: (kv[1], len(kv[0])))[0]

        # Indexar existentes por codigo y por nombre normalizado
        by_code = {m.codigo.upper(): m for m in TipoMuestra.objects.all()}
        by_norm_name = {norm_text(m.nombre): m for m in TipoMuestra.objects.all()}

        out: dict[str, TipoMuestra] = {}
        used_codes = set(by_code.keys())

        for key, display in sorted(preferred.items(), key=lambda kv: kv[1].lower()):
            existing = by_norm_name.get(key)
            if existing:
                if not existing.activo and not dry_run:
                    existing.activo = True
                    existing.save(update_fields=["activo"])
                    stats["muestras_reactivadas"] += 1
                # Actualizar nombre display si mejora
                if existing.nombre != display and not dry_run:
                    existing.nombre = display[:200]
                    existing.save(update_fields=["nombre"])
                    stats["muestras_renombradas"] += 1
                out[key] = existing
                stats["muestras_reutilizadas"] += 1
                continue

            code = material_codigo(display)
            base_code = code
            i = 2
            while code in used_codes:
                suffix = f"_{i}"
                code = (base_code[: 64 - len(suffix)] + suffix)
                i += 1

            if dry_run:
                # Objeto no persistido solo para dry-run de exámenes
                m = TipoMuestra(codigo=code, nombre=display[:200], activo=True)
                stats["muestras_creadas"] += 1
            else:
                m = TipoMuestra.objects.create(
                    codigo=code,
                    nombre=display[:200],
                    activo=True,
                )
                stats["muestras_creadas"] += 1
                self.stdout.write(f"  + muestra {code}: {display}")

            used_codes.add(code)
            by_code[code] = m
            by_norm_name[key] = m
            out[key] = m

        return out

    def _sync_examenes(self, rows, muestras, stats, dry_run: bool) -> set[int]:
        examenes = list(TipoExamen.objects.select_related("tipo_muestra_requerida").all())
        by_code = {e.codigo.upper(): e for e in examenes}
        by_name: dict[str, list[TipoExamen]] = defaultdict(list)
        for e in examenes:
            by_name[norm_text(e.nombre)].append(e)

        claimed: set[int] = set()
        csv_codes = {r["codigo"] for r in rows}

        # Pass 1: match by código IACA
        pending = []
        for r in rows:
            code = r["codigo"]
            exam = by_code.get(code)
            if exam is None:
                pending.append(r)
                continue
            self._apply_exam_update(exam, r, muestras, stats, dry_run, renamed=False)
            claimed.add(exam.pk)
            stats["examenes_actualizados_por_codigo"] += 1

        # Pass 2: match by nombre normalizado SOLO si ese nombre es único en el CSV.
        # Si hay varias filas con el mismo examen y distinto material/código IACA,
        # no adivinamos: se crean todas y el legado se desactiva.
        name_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            name_counts[norm_text(r["nombre"])] += 1

        still_pending = []
        for r in pending:
            key = norm_text(r["nombre"])
            if name_counts.get(key, 0) != 1:
                still_pending.append(r)
                stats["examenes_nombre_ambiguo_sin_match"] += 1
                continue
            candidates = [
                e
                for e in by_name.get(key, [])
                if e.pk not in claimed and e.codigo.upper() not in csv_codes
            ]
            candidates.sort(key=lambda e: (not e.activo, e.pk))
            if not candidates:
                still_pending.append(r)
                continue
            exam = candidates[0]
            old_code = exam.codigo
            by_code.pop(old_code.upper(), None)
            self._apply_exam_update(exam, r, muestras, stats, dry_run, renamed=True)
            by_code[r["codigo"]] = exam
            claimed.add(exam.pk)
            stats["examenes_actualizados_por_nombre"] += 1
            self.stdout.write(
                f"  ~ código {old_code} -> {r['codigo']} ({r['nombre']})"
            )

        # Pass 3: crear faltantes
        fallback_muestra = None
        for r in still_pending:
            mat_key = norm_text(r["material"])
            muestra = muestras.get(mat_key)
            if muestra is None:
                if fallback_muestra is None:
                    fallback_muestra = (
                        TipoMuestra.objects.filter(activo=True).order_by("id").first()
                    )
                    if fallback_muestra is None and not dry_run:
                        fallback_muestra = TipoMuestra.objects.create(
                            codigo="OTRO",
                            nombre="otro material",
                            activo=True,
                        )
                muestra = fallback_muestra
            if muestra is None:
                # dry-run sin muestras en BD
                muestra = TipoMuestra(codigo="OTRO", nombre="otro material", activo=True)

            if dry_run:
                stats["examenes_creados"] += 1
                continue

            exam = TipoExamen.objects.create(
                codigo=r["codigo"],
                nombre=r["nombre"][:200],
                tipo_muestra_requerida=muestra,
                activo=True,
                requiere_muestra=True,
            )
            claimed.add(exam.pk)
            by_code[r["codigo"]] = exam
            stats["examenes_creados"] += 1

        return claimed

    def _apply_exam_update(self, exam, row, muestras, stats, dry_run, renamed: bool):
        mat_key = norm_text(row["material"])
        muestra = muestras.get(mat_key)
        if muestra is None:
            # No debería pasar: materiales se crearon antes
            muestra = exam.tipo_muestra_requerida

        fields = []
        if exam.codigo != row["codigo"]:
            exam.codigo = row["codigo"]
            fields.append("codigo")
        if exam.nombre != row["nombre"]:
            exam.nombre = row["nombre"][:200]
            fields.append("nombre")
        if exam.tipo_muestra_requerida_id != getattr(muestra, "pk", None) and getattr(
            muestra, "pk", None
        ):
            exam.tipo_muestra_requerida = muestra
            fields.append("tipo_muestra_requerida")
        if not exam.activo:
            exam.activo = True
            fields.append("activo")
        if not exam.requiere_muestra:
            exam.requiere_muestra = True
            fields.append("requiere_muestra")

        if fields and not dry_run:
            exam.save(update_fields=fields)
        elif fields:
            stats["examenes_campos_a_cambiar"] += len(fields)

    def _deactivate_orphans(self, claimed: set[int], stats, dry_run: bool):
        qs = TipoExamen.objects.exclude(pk__in=claimed).filter(activo=True)
        count = qs.count()
        stats["examenes_desactivados"] = count
        if count and not dry_run:
            qs.update(activo=False)
            self.stdout.write(
                self.style.WARNING(f"  Desactivados (no están en CSV): {count}")
            )