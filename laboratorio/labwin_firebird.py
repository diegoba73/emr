"""
Parser Firebird LabWin4 -> estructuras compatibles con import_labwin_csv.
Sin PHI en logs. Solo lectura de CSV.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from laboratorio.labwin_csv import COLUMNA_A_CODIGO, LabwinOrder, LabwinPatient, format_protocolo_labwin
from laboratorio.labwin_firebird_scale import interpret_result_fld, load_results_catalog

# ABREV de un solo valor -> codigo LIMS (extiende COLUMNA_A_CODIGO).
# No incluir claves de paneles empaquetados (HEM/ION/BRR/ORI).
FB_SIMPLE_ABREV: dict[str, str] = {
    **{
        k.upper(): v
        for k, v in COLUMNA_A_CODIGO.items()
        if k.upper() not in {"HEM", "ION", "BRR", "ORI", "SED", "COA", "HEP"}
    },
    "URE": "UREA",
    "CRE": "CREATI",
    "GLU": "GLU",
    "COL": "COL_TOT",
    "TGL": "TG",
    "HDL": "HDL",
    "LDL": "LDL",
    "VLD": "VLDL",
    "LDLC": "LDL",
    "NHDLC": "COL_NO_LDL",
    "CHDL": "RATIO_CT_HDL",
    "CLDL": "LDL",
    "CVLDL": "VLDL",
    "COLRC": "COL_RESID",
    "RCH": "RATIO_CT_HDL",
    "CNOHDL": "COL_NO_LDL",
    "ASP": "TGO",
    "ALT": "TGP",
    "TGO": "TGO",
    "TGP": "TGP",
    "TPR": "TP",
    "KPT": "KPTT",
    "VDR": "VDRL",
    "PLP": "PLAQ",
    "RPQ": "PLAQ",
    "TROPO": "TROP_I",
    "TROPO I": "TROP_I",
    "CKM": "CPK_MB",
    "MIO": "MIOG",
    "BILI": "BILI",
    "PCRU": "PCR_US",
    "AMS": "AMIL",
    "AMI": "AMIL",
}

# Paneles empaquetados (RESULT pipe-separado) -> codigos por posicion 1-based (tipo RESULTS=1).
# None = omitir posicion (observaciones / no mapeable).
FB_PACKED_PANELS: dict[str, list[str | None]] = {
    "HEM": [
        "HEMATIES",
        "HTO",
        "HGB",
        "RDW",
        "LEUCO",
        "NEUT_CAY",
        "NEUT_SEG",
        "EOS",
        "BAS",
        "LINF",
        "MONO",
        None,
        None,
    ],
    "ION": ["NA", "K", "CL"],
    "BRR": ["BILI", None],
    "ORI": [
        "ORI_COLOR",
        "ORI_ASP",
        "ORI_PH",
        "ORI_DENS",
        None,
        "ORI_CET",
        None,
        "ORI_HEM",
        "ORI_BIL",
        "ORI_CONC",
    ],
}


def parse_fb_date(s: str) -> date | None:
    s = (s or "").strip().strip('"')
    if len(s) == 8 and s.isdigit():
        try:
            return datetime.strptime(s, "%Y%m%d").date()
        except ValueError:
            return None
    return None


def _is_active(row: dict) -> bool:
    deleted = (row.get("PRV_DELETEDRECORD_FLD") or "").strip().strip('"')
    return deleted in ("", "0", "False", "false")


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip().strip('"')


def resolve_simple_abrev(abrev: str) -> str | None:
    a = (abrev or "").strip()
    if not a:
        return None
    if a in FB_SIMPLE_ABREV:
        return FB_SIMPLE_ABREV[a]
    if a.upper() in FB_SIMPLE_ABREV:
        return FB_SIMPLE_ABREV[a.upper()]
    if a in COLUMNA_A_CODIGO:
        return COLUMNA_A_CODIGO[a]
    for k, v in COLUMNA_A_CODIGO.items():
        if k.lower() == a.lower() and k.lower() not in {"hem"}:
            return v
    return a


def unpack_result(abrev: str, raw: str) -> dict[str, str]:
    """Devuelve {codigo_lims: valor} sin PHI logging. Valor ya debe venir interpretado."""
    raw = (raw or "").strip()
    if not raw:
        return {}
    abrev_u = abrev.strip()
    if abrev_u in FB_PACKED_PANELS and "|" in raw:
        parts = raw.split("|")
        codes = FB_PACKED_PANELS[abrev_u]
        out: dict[str, str] = {}
        for i, code in enumerate(codes):
            if code is None or i >= len(parts):
                continue
            val = parts[i].strip()
            if not val or val in {"-", "--", "------------"}:
                continue
            out[code] = val
        return out
    code = resolve_simple_abrev(abrev_u)
    if not code or code in FB_PACKED_PANELS:
        if abrev_u in FB_PACKED_PANELS:
            return {}
        return {code: raw} if code else {}
    return {code: raw}


@dataclass
class FirebirdLoadStats:
    protocols_read: int = 0
    protocols_post: int = 0
    protocols_skipped_pre: int = 0
    protocols_skipped_in_wide: int = 0
    protocols_no_hclin: int = 0
    protocols_bad_hclin: int = 0
    orders_built: int = 0
    results_mapped: int = 0
    results_unmapped_abrev: int = 0
    results_scaled: int = 0
    results_textual: int = 0
    results_quarantined: int = 0
    deters_empty: int = 0
    patients: int = 0
    warnings: list[str] = field(default_factory=list)


def _map_scaled_result(
    abrev: str,
    raw: str,
    catalog: dict,
    lims_codes: set[str] | None,
    stats: FirebirdLoadStats,
) -> dict[str, str]:
    """Aplica escala LabWin y mapea a codigos LIMS. Cuarentena no se escribe."""
    abrev_u = (abrev or "").strip()
    outcomes = interpret_result_fld(abrev_u, raw, catalog)
    out: dict[str, str] = {}

    if abrev_u in FB_PACKED_PANELS and "|" in (raw or ""):
        codes = FB_PACKED_PANELS[abrev_u]
        for i, outcome in enumerate(outcomes):
            if i >= len(codes) or codes[i] is None:
                continue
            code = codes[i]
            emptyish = (not outcome.valor_clinico) or outcome.valor_clinico in {
                "-",
                "--",
                "------------",
            }
            if outcome.status == "quarantine" or emptyish:
                if outcome.status == "quarantine":
                    stats.results_quarantined += 1
                continue
            if lims_codes is not None and code not in lims_codes:
                stats.results_unmapped_abrev += 1
                continue
            out[code] = outcome.valor_clinico
            stats.results_mapped += 1
            if outcome.status == "ok":
                stats.results_scaled += 1
            else:
                stats.results_textual += 1
        return out

    if not outcomes:
        stats.results_unmapped_abrev += 1
        return {}
    outcome = outcomes[0]
    if outcome.status == "quarantine" or not outcome.valor_clinico:
        stats.results_quarantined += 1
        return {}
    code = resolve_simple_abrev(abrev_u)
    if not code or (code in FB_PACKED_PANELS and abrev_u in FB_PACKED_PANELS):
        stats.results_unmapped_abrev += 1
        return {}
    if lims_codes is not None and code not in lims_codes:
        stats.results_unmapped_abrev += 1
        return {}
    out[code] = outcome.valor_clinico
    stats.results_mapped += 1
    if outcome.status == "ok":
        stats.results_scaled += 1
    else:
        stats.results_textual += 1
    return out


def load_firebird_delta(
    datos_dir: Path,
    *,
    wide_protocols: set[str],
    since: date,
    lims_codes: set[str] | None = None,
) -> tuple[dict[str, LabwinPatient], list[LabwinOrder], FirebirdLoadStats]:
    """
    Carga protocolos Firebird con fecha > since y protocolo LW no presente en wide_protocols.
    Identidad: HCLIN_FLD como DNI (puente validado vs todo_labwin en analisis R2).
    Aplica escala decimal RESULTS.DECIMALES_FLD antes de mapear a LIMS.
    """
    datos_dir = Path(datos_dir)
    stats = FirebirdLoadStats()
    patients: dict[str, LabwinPatient] = {}
    orders: list[LabwinOrder] = []

    results_path = datos_dir / "RESULTS.csv"
    if results_path.exists():
        catalog = load_results_catalog(results_path)
    else:
        catalog = {}
        stats.warnings.append("RESULTS.csv ausente: escala decimal en cuarentena")

    deters: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with (datos_dir / "DETERS.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not _is_active(row):
                continue
            num = _cell(row, "NUMERO_FLD")
            abrev = _cell(row, "ABREV_FLD")
            res = _cell(row, "RESULT_FLD")
            if not num or not abrev:
                continue
            deters[num].append((abrev, res))

    hclin_demo: dict[str, tuple[str, str]] = {}
    with (datos_dir / "HCLINICA.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not _is_active(row):
                continue
            nid = _cell(row, "NUMERO_FLD")
            nombre = _cell(row, "NOMBRE_FLD")
            if nid and nombre:
                if "," in nombre:
                    ap, no = nombre.split(",", 1)
                    hclin_demo[nid] = (ap.strip(), no.strip())
                else:
                    hclin_demo[nid] = (nombre, "")

    with (datos_dir / "PACIENTES.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not _is_active(row):
                continue
            stats.protocols_read += 1
            num = _cell(row, "NUMERO_FLD")
            hclin = _cell(row, "HCLIN_FLD")
            fecha = parse_fb_date(_cell(row, "FECHA_FLD"))
            if not num or not fecha:
                continue
            if fecha <= since:
                stats.protocols_skipped_pre += 1
                continue
            lw = format_protocolo_labwin(fecha, num)
            if not lw:
                continue
            if lw in wide_protocols:
                stats.protocols_skipped_in_wide += 1
                continue
            stats.protocols_post += 1
            if not hclin:
                stats.protocols_no_hclin += 1
                stats.warnings.append(f"proto_sin_hclin fecha={fecha.isoformat()}")
                continue
            if not (hclin.isdigit() and 7 <= len(hclin) <= 8):
                stats.protocols_bad_hclin += 1
                stats.warnings.append(f"hclin_forma_invalida len={len(hclin)}")
                continue

            resultados: dict[str, str] = {}
            for abrev, raw in deters.get(num, []):
                if not raw:
                    stats.deters_empty += 1
                    continue
                mapped = _map_scaled_result(abrev, raw, catalog, lims_codes, stats)
                for code, val in mapped.items():
                    resultados[code] = val

            if not resultados:
                continue

            if hclin not in patients:
                ap, no = hclin_demo.get(hclin, ("", ""))
                patients[hclin] = LabwinPatient(
                    dni=hclin,
                    apellido=ap or "Sin apellido",
                    nombre=no or "Sin nombre",
                    telefono="",
                    direccion="",
                    fecha=fecha,
                )
            orders.append(
                LabwinOrder(
                    dni=hclin,
                    fecha=fecha,
                    numero_labwin=num,
                    protocolo=lw,
                    resultados=resultados,
                    paneles=[],
                )
            )
            stats.orders_built += 1

    stats.patients = len(patients)
    return patients, orders, stats
