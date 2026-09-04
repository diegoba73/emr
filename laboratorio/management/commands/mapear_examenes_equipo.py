"""
Asigna TipoExamen.equipo_analizador según laboratorio.equipos_lab.EXAMEN_A_EQUIPO.

Idempotente y seguro para producción: solo actualiza el FK equipo_analizador.
No crea lotes/targets demo, no desactiva MaterialControl.

Uso (producción, tras deploy del código):
  cd /srv/emr/app
  docker compose exec -T backend python manage.py mapear_examenes_equipo --dry-run
  docker compose exec -T backend python manage.py mapear_examenes_equipo --equipo CM260

AVISO: NO usar seed_qc_demo en producción si solo necesitás el mapeo —
ese comando también desactiva MaterialControl de equipos multiparámetro
y crea lotes/targets demo (QC-DEMO-*).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from laboratorio.equipos_lab import EXAMEN_A_EQUIPO, EXAMENES_POR_EQUIPO
from laboratorio.models import TipoExamen
from laboratorio.models_qc import EquipoAnalizador


class Command(BaseCommand):
    help = (
        "Mapea TipoExamen.equipo_analizador según EXAMEN_A_EQUIPO "
        "(solo update; no toca materiales ni lotes)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra qué se actualizaría, sin escribir.",
        )
        parser.add_argument(
            "--equipo",
            type=str,
            default="",
            help="Limitar a un código de equipo (ej. CM260).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        solo_equipo = (options.get("equipo") or "").strip().upper()

        equipos = {e.codigo: e for e in EquipoAnalizador.objects.all()}
        if solo_equipo and solo_equipo not in equipos:
            self.stderr.write(
                self.style.ERROR(
                    f"Equipo {solo_equipo!r} no existe en EquipoAnalizador. "
                    f"Disponibles: {', '.join(sorted(equipos)) or '(ninguno)'}"
                )
            )
            return

        mapping = EXAMEN_A_EQUIPO
        if solo_equipo:
            codigos = EXAMENES_POR_EQUIPO.get(solo_equipo, frozenset())
            mapping = {c: solo_equipo for c in codigos}

        updated = 0
        already = 0
        missing_exam = 0
        missing_eq = 0

        for codigo_ex, codigo_eq in sorted(mapping.items()):
            eq = equipos.get(codigo_eq)
            if not eq:
                missing_eq += 1
                self.stdout.write(
                    self.style.WARNING(f"  sin equipo {codigo_eq} para examen {codigo_ex}")
                )
                continue
            ex = TipoExamen.objects.filter(codigo=codigo_ex).first()
            if not ex:
                missing_exam += 1
                continue
            if ex.equipo_analizador_id == eq.id:
                already += 1
                continue
            prev = ex.equipo_analizador_id
            self.stdout.write(
                f"  {codigo_ex}: equipo_analizador {prev} → {eq.id} ({codigo_eq})"
            )
            if not dry_run:
                TipoExamen.objects.filter(pk=ex.pk).update(equipo_analizador_id=eq.id)
            updated += 1

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}mapear_examenes_equipo OK "
                f"updated={updated} already_ok={already} "
                f"examen_ausente={missing_exam} equipo_ausente={missing_eq}"
            )
        )
