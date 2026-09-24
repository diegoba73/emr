"""
Rectifica resultados LabWin importados desde Firebird con escala decimal incorrecta.

Por defecto solo dry-run (conteos). Con --apply escribe valor_obtenido / valor_numerico
y recalcula banderas clinicas. Sin PHI en logs.

Alcance tipico R2: --only-r2-delta (protocolos post-corte no presentes en todo_labwin).
"""
from __future__ import annotations

import csv
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from laboratorio.labwin_csv import format_protocolo_labwin, load_labwin_csv, parse_valor_numerico
from laboratorio.labwin_firebird import (
    FB_PACKED_PANELS,
    _cell,
    _is_active,
    parse_fb_date,
    resolve_simple_abrev,
)
from laboratorio.labwin_firebird_scale import interpret_result_fld, load_results_catalog
from laboratorio.management.commands.import_labwin_csv import _audit_labwin_batch, _set_digest
from laboratorio.models import ResultadoExamen, SolicitudExamen
from laboratorio.resultados_clinicos import calcular_es_critico, calcular_es_patologico


def _norm(text: str | None) -> str:
    return (text or "").strip()


def _nums_equal(a: str | None, b: str | None) -> bool:
    na = parse_valor_numerico(_norm(a) or "")
    nb = parse_valor_numerico(_norm(b) or "")
    if na is not None and nb is not None:
        return na == nb
    return _norm(a) == _norm(b)


def _is_finalized(sol: SolicitudExamen, res: ResultadoExamen) -> bool:
    return sol.estado in {"FINALIZADO", "INFORMADO_PARCIAL"} or bool(
        getattr(res, "fecha_validacion", None)
    ) or bool(getattr(res, "validado_por_id", None))


@dataclass
class ScaleFix:
    resultado_id: int
    codigo: str
    protocolo: str
    expected: str
    finalized: bool


class Command(BaseCommand):
    help = (
        "Corrige escala decimal LabWin Firebird en ResultadoExamen ya persistidos. "
        "Dry-run por defecto; --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument("datos_dir", type=str)
        parser.add_argument("--wide-csv", default="data/icpl/todo_labwin.csv")
        parser.add_argument("--since", default="2026-08-12")
        parser.add_argument(
            "--only-r2-delta",
            action="store_true",
            default=True,
            help="Solo delta R2 (default: on)",
        )
        parser.add_argument(
            "--all-firebird-overlap",
            action="store_true",
            help="Incluye todos los protocolos Firebird presentes en PG (no solo R2)",
        )
        parser.add_argument("--apply", action="store_true")
        parser.add_argument(
            "--include-finalized",
            action="store_true",
            help=(
                "Rectifica tambien FINALIZADO/validado. "
                "Necesario para LabWin R2: las ordenes LW- suelen estar FINALIZADO."
            ),
        )
        parser.add_argument("--batch-size", type=int, default=500)

    def handle(self, *args, **options):
        datos_dir = Path(options["datos_dir"]).expanduser().resolve()
        if not datos_dir.is_dir():
            raise CommandError(f"No existe: {datos_dir}")
        for req in ("DETERS.csv", "PACIENTES.csv", "RESULTS.csv"):
            if not (datos_dir / req).exists():
                raise CommandError(f"Falta {req}")

        only_r2 = not options["all_firebird_overlap"]
        since = date.fromisoformat(options["since"])
        wide_path = Path(options["wide_csv"]).expanduser().resolve()
        wide_protos: set[str] = set()
        if wide_path.exists():
            _, wide_orders, _ = load_labwin_csv(wide_path)
            wide_protos = {o.protocolo for o in wide_orders}

        catalog = load_results_catalog(datos_dir / "RESULTS.csv")
        deters: dict[str, list[tuple[str, str]]] = {}
        with (datos_dir / "DETERS.csv").open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                if not _is_active(row):
                    continue
                num = _cell(row, "NUMERO_FLD")
                abrev = _cell(row, "ABREV_FLD")
                res = _cell(row, "RESULT_FLD")
                if not num or not abrev or not res:
                    continue
                deters.setdefault(num, []).append((abrev, res))

        target_protos: dict[str, str] = {}
        with (datos_dir / "PACIENTES.csv").open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                if not _is_active(row):
                    continue
                num = _cell(row, "NUMERO_FLD")
                fecha = parse_fb_date(_cell(row, "FECHA_FLD"))
                if not num or not fecha:
                    continue
                lw = format_protocolo_labwin(fecha, num)
                if not lw:
                    continue
                if only_r2:
                    if fecha <= since or lw in wide_protos:
                        continue
                target_protos[lw] = num

        counts: Counter[str] = Counter()
        fixes: list[ScaleFix] = []

        sols = (
            SolicitudExamen.objects.filter(numero__in=list(target_protos.keys()))
            .prefetch_related("resultados__tipo_examen")
            .only("id", "numero", "estado")
        )
        sol_by_num = {s.numero: s for s in sols}
        counts["protocols_in_scope"] = len(target_protos)
        counts["protocols_in_db"] = len(sol_by_num)

        for lw, fb_num in target_protos.items():
            sol = sol_by_num.get(lw)
            if not sol:
                counts["protocol_missing_in_db"] += 1
                continue
            pg_by_code = {
                r.tipo_examen.codigo: r
                for r in sol.resultados.all()
                if getattr(r.tipo_examen, "codigo", None)
            }
            for abrev, raw in deters.get(fb_num, []):
                outcomes = interpret_result_fld(abrev, raw, catalog)
                abrev_u = abrev.strip()
                parts = raw.split("|") if "|" in raw else [raw]
                if abrev_u in FB_PACKED_PANELS and "|" in raw:
                    codes = FB_PACKED_PANELS[abrev_u]
                    pairs = []
                    for i, outcome in enumerate(outcomes):
                        if i < len(codes) and codes[i]:
                            tok = parts[i].strip() if i < len(parts) else ""
                            pairs.append((codes[i], outcome, tok))
                else:
                    code = resolve_simple_abrev(abrev_u)
                    if not code or code in FB_PACKED_PANELS:
                        continue
                    pairs = [(code, outcomes[0], raw)]

                for code, outcome, raw_token in pairs:
                    counts["pairs_checked"] += 1
                    if outcome.status == "quarantine" or not outcome.valor_clinico:
                        counts["quarantine_skipped"] += 1
                        continue
                    res = pg_by_code.get(code)
                    if not res:
                        counts["pg_missing"] += 1
                        continue
                    pg_val = _norm(res.valor_obtenido)
                    expected = _norm(outcome.valor_clinico)
                    raw_n = _norm(raw_token)
                    finalized = _is_finalized(sol, res)

                    if _nums_equal(pg_val, expected):
                        counts["already_correct"] += 1
                        continue

                    # Caso clinico: PG tiene el crudo Firebird y la escala cambia el valor
                    if raw_n and _nums_equal(pg_val, raw_n) and not _nums_equal(raw_n, expected):
                        counts["scale_error"] += 1
                        if finalized and not options["include_finalized"]:
                            counts["scale_error_skipped_finalized"] += 1
                            continue
                        fixes.append(
                            ScaleFix(
                                resultado_id=res.id,
                                codigo=code,
                                protocolo=lw,
                                expected=expected,
                                finalized=finalized,
                            )
                        )
                        continue

                    counts["ambiguous_skipped"] += 1

        counts["fixable"] = len(fixes)
        self.stdout.write("== rectify_labwin_firebird_scale ==")
        self.stdout.write(f"  modo: {'APPLY' if options['apply'] else 'DRY-RUN'}")
        self.stdout.write(f"  alcance: {'r2-delta' if only_r2 else 'all-overlap'}")
        for key in sorted(counts):
            self.stdout.write(f"  {key}: {counts[key]}")

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run: no se modifico la base. Reejecutar con --apply para corregir."
                )
            )
            return

        if not fixes:
            self.stdout.write(self.style.SUCCESS("Nada para corregir."))
            return

        batch_id = str(uuid.uuid4())
        file_sha = _set_digest(
            [
                "rectify_labwin_firebird_scale",
                str(datos_dir),
                options["since"],
                "r2" if only_r2 else "all",
            ]
        )
        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha,
            success=True,
            metadata={
                "status": "started",
                "source": "rectify_firebird_scale",
                "fixable_planned": len(fixes),
                "include_finalized": bool(options["include_finalized"]),
            },
        )

        updated = 0
        batch = max(1, options["batch_size"])
        fix_ids = [f.resultado_id for f in fixes]
        expected_by_id = {f.resultado_id: f.expected for f in fixes}

        try:
            for i in range(0, len(fix_ids), batch):
                chunk_ids = fix_ids[i : i + batch]
                with transaction.atomic():
                    rows = list(
                        ResultadoExamen.objects.select_related("tipo_examen").filter(
                            id__in=chunk_ids
                        )
                    )
                    for res in rows:
                        expected = expected_by_id[res.id]
                        res.valor_obtenido = expected[:255]
                        res.valor_numerico = parse_valor_numerico(expected)
                        pat = calcular_es_patologico(
                            res.valor_numerico,
                            res.rango_min_snapshot,
                            res.rango_max_snapshot,
                        )
                        if pat is not None:
                            res.es_patologico = pat
                        crit = calcular_es_critico(
                            res.valor_numerico,
                            res.valor_critico_min_snapshot,
                            res.valor_critico_max_snapshot,
                        )
                        if crit is not None:
                            res.es_critico = crit
                    ResultadoExamen.objects.bulk_update(
                        rows,
                        [
                            "valor_obtenido",
                            "valor_numerico",
                            "es_patologico",
                            "es_critico",
                        ],
                        batch_size=batch,
                    )
                    updated += len(rows)
        except Exception as exc:
            _audit_labwin_batch(
                batch_id=batch_id,
                file_sha256=file_sha,
                success=False,
                error_message=type(exc).__name__,
                metadata={
                    "status": "failed_partial",
                    "source": "rectify_firebird_scale",
                    "updated_before_error": updated,
                },
            )
            raise

        _audit_labwin_batch(
            batch_id=batch_id,
            file_sha256=file_sha,
            success=True,
            metadata={
                "status": "applied",
                "source": "rectify_firebird_scale",
                "updated": updated,
                "protocols_hmac_set_sha256": _set_digest(
                    sorted({f.protocolo for f in fixes})
                ),
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Rectificados: {updated}"))
        self.stdout.write(f"  Lote auditoria: {batch_id}")
