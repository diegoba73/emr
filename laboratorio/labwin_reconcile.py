"""
Reconciliación LabWin CSV ↔ BD (solo lectura).

No escribe PostgreSQL. No emite PHI/PII ni valores clínicos.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

from laboratorio.labwin_csv import (
    DNI_RE,
    SKIP_DNI,
    format_protocolo_labwin,
    is_empty,
    iter_labwin_rows,
    load_labwin_csv,
    normalize_dni,
    parse_fecha,
)


def normalize_valor_comparacion(raw: str | None) -> str:
    """Normaliza valor para igualdad estructural (sin exponer el valor)."""
    text = (raw or "").strip()
    if is_empty(text):
        return ""
    compact = text.replace("\u00a0", " ").strip()
    compact = compact.replace(",", ".")
    return compact


@dataclass
class ReconcileStats:
    csv_orders: int = 0
    csv_unique_patients: int = 0
    csv_patients_with_orders: int = 0
    csv_patients_without_orders: int = 0
    order_identical: int = 0
    order_missing_in_db: int = 0
    order_patient_mismatch: int = 0
    order_date_mismatch: int = 0
    order_result_diff: int = 0
    result_missing_in_db: int = 0
    result_extra_in_db: int = 0
    order_extra_in_db: int = 0
    proto_dup_rows_raw: int = 0
    proto_dup_identical: int = 0
    proto_dup_divergent: int = 0
    proto_ambiguous: int = 0
    patients_skip_dni: int = 0
    patients_invalid_dni: int = 0
    warnings: list[str] = field(default_factory=list)


def _row_content_fingerprint(resultados: dict[str, str], fecha: date | None, dni: str) -> tuple:
    """Huella in-memory (no se imprime). Incluye dni normalizado solo en proceso."""
    items = tuple(sorted((c, normalize_valor_comparacion(v)) for c, v in resultados.items()))
    return (dni, fecha.isoformat() if fecha else "", items)


def analyze_csv_duplicates_and_patients(csv_path: Path, encoding: str = "utf-8-sig") -> ReconcileStats:
    """Analiza CSV sin tocar BD: dups pre-first-wins y pacientes sin orden."""
    stats = ReconcileStats()
    patients, orders, load_stats = load_labwin_csv(csv_path, encoding=encoding)
    stats.csv_unique_patients = load_stats.unique_patients
    stats.csv_orders = load_stats.orders
    stats.patients_skip_dni = load_stats.dni_omitidos_revision
    stats.patients_invalid_dni = load_stats.dni_invalidos

    with_orders = {o.dni for o in orders}
    stats.csv_patients_with_orders = len(with_orders)
    stats.csv_patients_without_orders = len(set(patients) - with_orders)

    # Pre-first-wins: todas las filas que generan protocolo válido (con o sin resultados)
    by_proto: dict[str, list[tuple]] = defaultdict(list)
    for _line_no, row in iter_labwin_rows(csv_path, encoding=encoding):
        dni = normalize_dni(row.get("Nº doc."))
        if not dni or dni in SKIP_DNI or not DNI_RE.match(dni):
            continue
        fecha = parse_fecha(row.get("Fecha"))
        if fecha is None:
            continue
        numero = (row.get("Número") or "").strip()
        proto = format_protocolo_labwin(fecha, numero)
        if not proto:
            continue
        # Resultados mapeados como haría el importador (sin EAB aquí para fingerprint de fila base;
        # usamos load path completo vía segunda pasada de orders agrupados)
        from laboratorio.labwin_csv import _pick_resultados, extraer_eab_layout_b

        resultados = _pick_resultados(row)
        eab = extraer_eab_layout_b(row)
        if eab:
            resultados = {**resultados, **eab[0]}
        by_proto[proto].append(_row_content_fingerprint(resultados, fecha, dni))

    dup_protos = {p: fps for p, fps in by_proto.items() if len(fps) > 1}
    stats.proto_dup_rows_raw = sum(len(fps) - 1 for fps in dup_protos.values())
    for fps in dup_protos.values():
        unique_fps = set(fps)
        if len(unique_fps) == 1:
            stats.proto_dup_identical += 1
        elif len(unique_fps) > 1:
            # mismo dni+fecha+resultados distintos, o distinto dni
            dnis = {fp[0] for fp in unique_fps}
            if len(dnis) > 1:
                stats.proto_ambiguous += 1
            else:
                stats.proto_dup_divergent += 1
    return stats


def reconcile_orders_against_db(
    csv_path: Path,
    *,
    encoding: str = "utf-8-sig",
    lw_queryset=None,
) -> ReconcileStats:
    """
    Compara órdenes CSV (first-wins) contra SolicitudExamen LW en BD.

    ``lw_queryset`` opcional para tests; por defecto filtra numero LIKE LW-%.
    """
    from laboratorio.models import ResultadoExamen, SolicitudExamen

    stats = analyze_csv_duplicates_and_patients(csv_path, encoding=encoding)
    _patients, orders, _load = load_labwin_csv(csv_path, encoding=encoding)

    # first-wins
    seen: set[str] = set()
    csv_by_proto: dict[str, object] = {}
    for order in orders:
        if order.protocolo in seen:
            continue
        seen.add(order.protocolo)
        csv_by_proto[order.protocolo] = order

    qs = lw_queryset
    if qs is None:
        qs = SolicitudExamen.objects.filter(numero__startswith="LW-").select_related("paciente")

    db_by_numero = {s.numero: s for s in qs if s.numero}
    stats.order_extra_in_db = sum(1 for n in db_by_numero if n not in csv_by_proto)

    # Prefetch resultados para órdenes CSV presentes en BD
    present = [n for n in csv_by_proto if n in db_by_numero]
    res_rows = (
        ResultadoExamen.objects.filter(solicitud__numero__in=present)
        .select_related("tipo_examen", "solicitud")
        .only(
            "valor_obtenido",
            "solicitud__numero",
            "tipo_examen__codigo",
        )
    )
    db_res: dict[str, dict[str, str]] = defaultdict(dict)
    for r in res_rows:
        codigo = r.tipo_examen.codigo
        db_res[r.solicitud.numero][codigo] = normalize_valor_comparacion(r.valor_obtenido)

    for proto, order in csv_by_proto.items():
        sol = db_by_numero.get(proto)
        if sol is None:
            stats.order_missing_in_db += 1
            continue
        dni_db = normalize_dni(getattr(sol.paciente, "dni", "") or "")
        if dni_db != order.dni:
            stats.order_patient_mismatch += 1
            continue
        fecha_db = sol.fecha_solicitud.date() if sol.fecha_solicitud else None
        if fecha_db != order.fecha:
            stats.order_date_mismatch += 1
            # sigue evaluando resultados
        csv_map = {
            c: normalize_valor_comparacion(v) for c, v in order.resultados.items()
        }
        db_map = db_res.get(proto, {})
        csv_codes = set(csv_map)
        db_codes = set(db_map)
        missing = csv_codes - db_codes
        extra = db_codes - csv_codes
        common = csv_codes & db_codes
        value_diff = sum(1 for c in common if csv_map[c] != db_map[c])
        stats.result_missing_in_db += len(missing)
        stats.result_extra_in_db += len(extra)
        if missing or extra or value_diff or fecha_db != order.fecha:
            if value_diff or missing or extra:
                stats.order_result_diff += 1
            if fecha_db != order.fecha and not (missing or extra or value_diff):
                pass  # already counted date_mismatch
        if not missing and not extra and value_diff == 0 and dni_db == order.dni and fecha_db == order.fecha:
            stats.order_identical += 1

    return stats


def stats_as_public_dict(stats: ReconcileStats) -> dict[str, int]:
    """Solo enteros agregados — apto para logs/reportes."""
    return {
        "csv_orders": stats.csv_orders,
        "csv_unique_patients": stats.csv_unique_patients,
        "csv_patients_with_orders": stats.csv_patients_with_orders,
        "csv_patients_without_orders": stats.csv_patients_without_orders,
        "order_identical": stats.order_identical,
        "order_missing_in_db": stats.order_missing_in_db,
        "order_patient_mismatch": stats.order_patient_mismatch,
        "order_date_mismatch": stats.order_date_mismatch,
        "order_result_diff": stats.order_result_diff,
        "result_missing_in_db": stats.result_missing_in_db,
        "result_extra_in_db": stats.result_extra_in_db,
        "order_extra_in_db": stats.order_extra_in_db,
        "proto_dup_rows_raw": stats.proto_dup_rows_raw,
        "proto_dup_identical": stats.proto_dup_identical,
        "proto_dup_divergent": stats.proto_dup_divergent,
        "proto_ambiguous": stats.proto_ambiguous,
        "patients_skip_dni": stats.patients_skip_dni,
        "patients_invalid_dni": stats.patients_invalid_dni,
    }
