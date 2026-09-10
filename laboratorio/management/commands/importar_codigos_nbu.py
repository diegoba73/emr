"""
Asigna codigo_nbu a TipoExamen emparejando el nombre/muestra con el Nomenclador Bioquímico Único.

No modifica TipoExamen.codigo (código interno/IACA).

Uso:
    python manage.py importar_codigos_nbu --dry-run
    python manage.py importar_codigos_nbu
    python manage.py importar_codigos_nbu --report /tmp/nbu_match.csv
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from laboratorio.models import TipoExamen
from laboratorio.nbu_match import (
    DEFAULT_NBU_CSV,
    ExamRow,
    load_nbu_catalog,
    match_catalog,
    ub_map,
)


class Command(BaseCommand):
    help = (
        "Completa TipoExamen.codigo_nbu y ub_nbu emparejando nombre/muestra "
        "contra el Nomenclador Bioquímico Único. No toca el código interno/IACA."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--nbu-csv",
            default=str(DEFAULT_NBU_CSV),
            help="CSV del nomenclador (codigo_nbu,nombre,frecuencia,ub).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sin persistir.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sobrescribe codigo_nbu ya cargado.",
        )
        parser.add_argument(
            "--min-score",
            type=float,
            default=94.0,
            help="Puntaje mínimo para asignación automática.",
        )
        parser.add_argument(
            "--min-margin",
            type=float,
            default=4.0,
            help="Diferencia mínima contra el segundo candidato.",
        )
        parser.add_argument(
            "--report",
            default="",
            help="Ruta CSV de reporte (auto/review/unmatched).",
        )
        parser.add_argument(
            "--incluir-inactivos",
            action="store_true",
            help="También procesa exámenes inactivos.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["nbu_csv"])
        if not csv_path.is_file():
            raise CommandError(f"No existe el CSV NBU: {csv_path}")

        dry_run = options["dry_run"]
        force = options["force"]
        catalog = load_nbu_catalog(csv_path)
        ubs = ub_map(catalog)
        qs = TipoExamen.objects.select_related("tipo_muestra_requerida")
        if not options["incluir_inactivos"]:
            qs = qs.filter(activo=True)

        exams = [
            ExamRow(
                exam_id=e.pk,
                codigo=e.codigo,
                nombre=e.nombre,
                muestra=(e.tipo_muestra_requerida.nombre if e.tipo_muestra_requerida_id else ""),
                activo=e.activo,
            )
            for e in qs.order_by("nombre", "codigo")
        ]
        results = match_catalog(
            exams,
            catalog,
            min_score=options["min_score"],
            min_margin=options["min_margin"],
        )

        auto = [r for r in results if r.auto]
        review = [r for r in results if r.rule == "review"]
        unmatched = [r for r in results if r.rule == "unmatched"]

        updated = 0
        ub_filled = 0
        skipped_existing = 0
        by_id = {e.pk: e for e in qs}

        def _ub_decimal(code: str):
            raw = ubs.get(code or "")
            if not raw:
                return None
            try:
                return Decimal(str(raw).replace(",", "."))
            except (InvalidOperation, ValueError):
                return None

        with transaction.atomic():
            for r in auto:
                exam = by_id.get(r.exam.exam_id)
                if exam is None or r.practica is None:
                    continue
                if exam.codigo_nbu and not force and exam.codigo_nbu != r.practica.codigo_nbu:
                    skipped_existing += 1
                    continue
                new_code = r.practica.codigo_nbu
                new_ub = _ub_decimal(new_code)
                changed = []
                if exam.codigo_nbu != new_code:
                    exam.codigo_nbu = new_code
                    changed.append("codigo_nbu")
                if new_ub is not None and exam.ub_nbu != new_ub:
                    exam.ub_nbu = new_ub
                    changed.append("ub_nbu")
                    ub_filled += 1
                if changed:
                    if not dry_run:
                        exam.save(update_fields=changed)
                    updated += 1

            # U.B. para códigos NBU ya cargados que no re-matchearon (o quedaron en revisión).
            for exam in by_id.values():
                if not exam.codigo_nbu:
                    continue
                new_ub = _ub_decimal(exam.codigo_nbu)
                if new_ub is None or exam.ub_nbu == new_ub:
                    continue
                exam.ub_nbu = new_ub
                if not dry_run:
                    exam.save(update_fields=["ub_nbu"])
                ub_filled += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            f"NBU prácticas: {len(catalog)} | exámenes: {len(exams)} | "
            f"auto: {len(auto)} | revisión: {len(review)} | sin match: {len(unmatched)}"
        )
        msg = f"{'Dry-run — se asignarían' if dry_run else 'Asignados/actualizados'} NBU: {updated}"
        if ub_filled:
            msg += f" | U.B. completadas: {ub_filled}"
        if skipped_existing:
            msg += f" (NBU previo conservado: {skipped_existing})"
        self.stdout.write(self.style.SUCCESS(msg) if not dry_run else self.style.WARNING(msg))

        report_path = options["report"]
        if report_path:
            self._write_report(Path(report_path), results)
            self.stdout.write(f"Reporte: {report_path}")

    def _write_report(self, path: Path, results) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "estado",
                "examen_id",
                "codigo_iaca",
                "nombre_examen",
                "muestra",
                "codigo_nbu",
                "nombre_nbu",
                "ub",
                "score",
                "rule",
                "segundo_codigo",
                "segundo_nombre",
                "segundo_score",
            ])
            for r in results:
                estado = "auto" if r.auto else r.rule
                w.writerow([
                    estado,
                    r.exam.exam_id,
                    r.exam.codigo,
                    r.exam.nombre,
                    r.exam.muestra,
                    r.practica.codigo_nbu if r.practica else "",
                    r.practica.nombre if r.practica else "",
                    r.practica.ub if r.practica else "",
                    f"{r.score:.1f}",
                    r.rule,
                    r.second_codigo,
                    r.second_nombre,
                    f"{r.second_score:.1f}",
                ])
