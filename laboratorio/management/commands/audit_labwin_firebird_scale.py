"""
Auditoria solo lectura: detecta resultados LabWin Firebird con error de escala.
No modifica PostgreSQL. Emite solo conteos agregados (sin PHI).
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from laboratorio.labwin_csv import format_protocolo_labwin, load_labwin_csv, parse_valor_numerico
from laboratorio.labwin_firebird import (
    FB_PACKED_PANELS,
    _cell,
    _is_active,
    parse_fb_date,
    resolve_simple_abrev,
)
from laboratorio.labwin_firebird_scale import interpret_result_fld, load_results_catalog
from laboratorio.models import SolicitudExamen


def _norm(text: str | None) -> str:
    return (text or "").strip()


def _nums_equal(a: str | None, b: str | None) -> bool:
    na = parse_valor_numerico(_norm(a) or "")
    nb = parse_valor_numerico(_norm(b) or "")
    if na is not None and nb is not None:
        return na == nb
    return _norm(a) == _norm(b)


class Command(BaseCommand):
    help = (
        "Compara DETERS/RESULTS (escala correcta) vs ResultadoExamen LW- en BD. "
        "Solo lectura; solo conteos."
    )

    def add_arguments(self, parser):
        parser.add_argument("datos_dir", type=str)
        parser.add_argument("--wide-csv", default="data/icpl/todo_labwin.csv")
        parser.add_argument("--since", default="2026-08-12")
        parser.add_argument(
            "--only-r2-delta",
            action="store_true",
            help="Solo protocolos Firebird posteriores a --since y ausentes del wide CSV",
        )

    def handle(self, *args, **options):
        datos_dir = Path(options["datos_dir"]).expanduser().resolve()
        if not datos_dir.is_dir():
            raise CommandError(f"No existe: {datos_dir}")
        for req in ("DETERS.csv", "PACIENTES.csv", "RESULTS.csv"):
            if not (datos_dir / req).exists():
                raise CommandError(f"Falta {req}")

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
                if options["only_r2_delta"]:
                    if fecha <= since or lw in wide_protos:
                        continue
                target_protos[lw] = num

        counts: Counter[str] = Counter()
        if not target_protos:
            self.stdout.write("Sin protocolos en alcance.")
            return

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
            pg_by_code = {}
            for r in sol.resultados.all():
                code = getattr(r.tipo_examen, "codigo", None)
                if code:
                    pg_by_code[code] = r

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
                        counts["fb_unmapped"] += 1
                        continue
                    pairs = [(code, outcomes[0], raw)]

                for code, outcome, raw_token in pairs:
                    counts["pairs_checked"] += 1
                    if outcome.status == "quarantine":
                        counts["quarantine"] += 1
                        continue
                    if outcome.status in ("textual", "passthrough") and outcome.valor_numerico is None:
                        counts["textual_or_structured"] += 1
                    res = pg_by_code.get(code)
                    if not res:
                        counts["pg_missing_result"] += 1
                        continue
                    pg_val = _norm(res.valor_obtenido)
                    expected = _norm(outcome.valor_clinico)
                    raw_n = _norm(raw_token)

                    finalized = sol.estado in {
                        "FINALIZADO",
                        "INFORMADO_PARCIAL",
                    } or bool(getattr(res, "fecha_validacion", None)) or bool(
                        getattr(res, "validado_por_id", None)
                    )

                    if _nums_equal(pg_val, expected):
                        counts["correct"] += 1
                        if finalized:
                            counts["correct_finalized"] += 1
                        continue

                    if raw_n and _nums_equal(pg_val, raw_n) and not _nums_equal(raw_n, expected):
                        counts["scale_error"] += 1
                        if finalized:
                            counts["scale_error_finalized_or_informed"] += 1
                        continue

                    counts["ambiguous_mismatch"] += 1
                    if finalized:
                        counts["ambiguous_finalized_or_informed"] += 1

        self.stdout.write("== audit_labwin_firebird_scale (agregados, sin PHI) ==")
        for key in sorted(counts):
            self.stdout.write(f"  {key}: {counts[key]}")
        self.stdout.write(self.style.SUCCESS("Auditoria finalizada (sin escrituras)."))
