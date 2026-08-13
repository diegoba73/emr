"""
Lectura del export LabWin ``todo_labwin.csv``.

No escribe en la base. El mapeo de columnas fue confirmado con el usuario.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

# DNI con personas distintas en el CSV: no importar hasta revisión manual.
SKIP_DNI = frozenset({"10378931", "12834465"})

DNI_RE = re.compile(r"^\d{5,11}$")
NUMERO_RE = re.compile(r"^(\d+)")

EMPTY_MARKERS = frozenset(
    {
        "",
        "------------",
        "-",
        "--",
        "---",
        "n/a",
        "N/A",
        "NULL",
        "-11",
        "-11.0",
    }
)

# Columna LabWin (header uniquificado) → código TipoExamen.
# Confirmado. No incluye EAB, serología, cultivos ni flags COA/HEP/PLP.
COLUMNA_A_CODIGO: dict[str, str] = {
    "hem": "HEMATIES",
    "hto": "HTO",
    "hgb": "HGB",
    "rdw": "RDW",
    "leu": "LEUCO",
    "nca": "NEUT_CAY",
    "nse": "NEUT_SEG",
    "eos": "EOS",
    "bas": "BAS",
    "lin": "LINF",
    "mon": "MONO",
    "GLU": "GLU",
    "URE": "UREA",
    "CRE": "CREATI",
    "AUR": "AU",
    "CPK": "CPK",
    "TROPO": "TROP_I",
    "CKM": "CPK_MB",
    "MIO": "MIOG",
    "CAI": "CA_ION",
    "Na": "NA",
    "K": "K",
    "Cl": "CL",
    "MGS": "MG",
    "ACL": "LACT",
    "PCRU": "PCR_US",
    "HGY": "HBA1C",
    "ERI": "VSG",
    "LDH": "LDH",
    "GGT": "GGT",
    "FOS": "P",
    "CAS": "CA",
    "FER": "FERR",
    "FET": "FERRIT",
    "LPA": "LPA",
    "TSH": "TSH",
    "T3": "T3",
    "T4": "T4",
    "T4L": "T4L",
    "BNP": "PROBNP",
    "PSA": "PSA",
    "V25": "VITD",
    "B12": "B12",
    "PRO": "PROT_T",
    "ALB": "ALB",
    "DMD": "DDIM",
    "PXE. PRO": "PROT_T",
    "PXE. ALB": "ELP_ALB",
    "PXE. A1": "ELP_A1",
    "PXE. A2": "ELP_A2",
    "PXE. B1": "ELP_B1",
    "PXE. B2": "ELP_B2",
    "PXE. G": "ELP_GAM",
    "PXE. com": "ELP_CONC",
    "IOU NaU -": "NA_U",
    "KU": "K_U",
    "ClU": "CL_U",
    "ALB-U": "MICROALB",
    "ALB-U24": "MICROALB",
    "PRU": "PROT_U_AZ",
    "ORI.Col": "ORI_COLOR",
    "ORI.asp": "ORI_ASP",
    "ORI.pH": "ORI_PH",
    "ORI.dens": "ORI_DENS",
    "ORI.hemg": "ORI_HEM",
    "ORI.bil": "ORI_BIL",
    "ORI.cc": "ORI_CET",
    "URO": "ORI_CONC",
}

# Si dos columnas LabWin caen en el mismo código, gana la más específica.
PRIORIDAD_COLUMNA: dict[str, int] = {
    "PXE. PRO": 20,
    "PRO": 10,
    "ALB-U24": 20,
    "ALB-U": 10,
}

PACIENTE_HEADERS = frozenset(
    {
        "Número",
        "Fecha",
        "Nº doc.",
        "Apellido y nombre",
        "Sexo",
        "F. nacim.",
        "Teléfono",
        "Localidad",
        "Celular",
    }
)


@dataclass
class LabwinPatient:
    dni: str
    apellido: str
    nombre: str
    telefono: str
    direccion: str
    fecha: date | None
    source_line: int = 0


@dataclass
class LabwinOrder:
    dni: str
    fecha: date
    numero_labwin: str
    protocolo: str
    resultados: dict[str, str]
    paneles: list[str] = field(default_factory=list)
    source_line: int = 0


@dataclass
class LabwinStats:
    lines_read: int = 0
    rows_parsed: int = 0
    rows_sin_resultado: int = 0
    dni_vacios: int = 0
    dni_invalidos: int = 0
    dni_omitidos_revision: int = 0
    unique_patients: int = 0
    orders: int = 0
    eab_art: int = 0
    eab_ven: int = 0
    eab_omitido_layout_viejo: int = 0
    warnings: list[str] = field(default_factory=list)


def uniquify_headers(headers: list[str]) -> list[str]:
    seen: Counter[str] = Counter()
    out: list[str] = []
    for raw in headers:
        h = (raw or "").strip()
        seen[h] += 1
        out.append(h if seen[h] == 1 else f"{h}#{seen[h]}")
    return out


def is_empty(val: str | None) -> bool:
    v = (val or "").strip()
    if v in EMPTY_MARKERS or set(v) <= {"-", " "}:
        return True
    compact = v.replace(",", ".")
    return compact in EMPTY_MARKERS


def normalize_dni(raw: str | None) -> str:
    return re.sub(r"[.\s]", "", (raw or "").strip())


def split_nombre(raw: str | None) -> tuple[str, str]:
    text = (raw or "").strip().strip('"')
    if not text:
        return "", ""
    if "," in text:
        ape, nom = text.split(",", 1)
        return ape.strip().upper(), nom.strip().upper()
    parts = text.split()
    if len(parts) >= 2:
        return parts[0].upper(), " ".join(parts[1:]).upper()
    return text.upper(), ""


def parse_fecha(raw: str | None) -> date | None:
    text = (raw or "").strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_numero_seq(numero_labwin: str) -> int | None:
    match = NUMERO_RE.match((numero_labwin or "").strip())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def format_protocolo_labwin(fecha: date, numero_labwin: str) -> str | None:
    seq = parse_numero_seq(numero_labwin)
    if seq is None:
        return None
    return f"LW-{fecha.year}-{seq:05d}"


def telefono_desde_fila(celular: str, telefono: str) -> str:
    if not is_empty(celular):
        return celular.strip()
    if not is_empty(telefono):
        return telefono.strip()
    return ""


def parse_valor_numerico(raw: str) -> Decimal | None:
    text = (raw or "").strip()
    if not text:
        return None
    text = text.replace(" ", "").replace("\u00a0", "")
    text = text.lstrip("<>≤≥")
    if text.startswith("+"):
        text = text[1:]
    if re.match(r"^-?\d{1,3}(\.\d{3})+,\d+$", text):
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    if not re.match(r"^-?\d+(\.\d+)?$", text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


# Columnas LabWin del perfil EAB (solo se importan si los valores coinciden
# con gases reales: pH~7.4, pCO2 mmHg, BE -30..+30). El export 2022-2025
# trae las mismas cabeceras con otro orden interno y se omite.
EAB_CAMPOS = (
    ("pH", "PH"),
    ("Ox", "PO2"),
    ("pCO2", "PCO2"),
    ("Sat", "SAT_O2"),
    ("Bic", "HCO3"),
    ("Eb", "BE"),
)


def eab_es_layout_coherente(ph: Decimal | None, pco2: Decimal | None, eb: Decimal | None) -> bool:
    """pH y pCO2 en rango de gases; BE opcional (a veces viene vacío o como -11)."""
    if ph is None or pco2 is None:
        return False
    if not (Decimal("6.8") <= ph <= Decimal("7.8")):
        return False
    if not (Decimal("15") <= pco2 <= Decimal("130")):
        return False
    if eb is not None and not (Decimal("-30") <= eb <= Decimal("30")):
        return False
    return True


def eab_parece_layout_viejo(ph: Decimal | None, pco2: Decimal | None, eb: Decimal | None) -> bool:
    """Cabeceras pH/Ox/pCO2/Sat/Bic/Eb con valores corridos (pCO2≈BE, Eb≈800-1000)."""
    if ph is None or not (Decimal("6.8") <= ph <= Decimal("7.8")):
        return False
    pco2_como_be = pco2 is not None and Decimal("-15") <= pco2 <= Decimal("15")
    eb_como_sat10 = eb is not None and eb >= Decimal("200")
    return bool(pco2_como_be or eb_como_sat10)


def inferir_tipo_eab(po2: Decimal | None, sat: Decimal | None) -> str:
    """Regla acordada: Sat≥95 o pO2≥80 → ART; si no → VEN."""
    if sat is not None and sat >= Decimal("95"):
        return "ART"
    if po2 is not None and po2 >= Decimal("80"):
        return "ART"
    return "VEN"


def extraer_eab_layout_b(row: dict[str, str]) -> tuple[dict[str, str], str] | None:
    """Devuelve (resultados código LIMS, panel) o None si no es EAB coherente."""
    valores: dict[str, str] = {}
    nums: dict[str, Decimal | None] = {}
    for col, _pref in EAB_CAMPOS:
        raw = (row.get(col) or "").strip()
        if col == "Eb" and raw.startswith("--"):
            raw = "-" + raw.lstrip("-")
        # En EAB, -11 es un BE clínico plausible; no usar el marcador vacío global.
        if col == "Eb" and raw in {"-11", "-11.0"}:
            num: Decimal | None = Decimal("-11")
        elif is_empty(raw):
            nums[col] = None
            continue
        else:
            num = parse_valor_numerico(raw)
        nums[col] = num
        if num is None:
            continue
        valores[col] = raw
    if not eab_es_layout_coherente(nums.get("pH"), nums.get("pCO2"), nums.get("Eb")):
        return None
    tipo = inferir_tipo_eab(nums.get("Ox"), nums.get("Sat"))
    out: dict[str, str] = {}
    for col, pref in EAB_CAMPOS:
        if col not in valores:
            continue
        out[f"{pref}_{tipo}"] = valores[col]
    if not out:
        return None
    panel = "PAN_EAB_ART" if tipo == "ART" else "PAN_EAB_VEN"
    return out, panel


def _pick_resultados(row: dict[str, str]) -> dict[str, str]:
    chosen: dict[str, tuple[int, str, str]] = {}
    for col, codigo in COLUMNA_A_CODIGO.items():
        val = row.get(col)
        if is_empty(val):
            continue
        prio = PRIORIDAD_COLUMNA.get(col, 0)
        prev = chosen.get(codigo)
        if prev is None or prio >= prev[0]:
            chosen[codigo] = (prio, col, val.strip())
    return {codigo: val for codigo, (_p, _c, val) in chosen.items()}


def _row_dict(headers: list[str], values: list[str]) -> dict[str, str]:
    return {h: (values[i] if i < len(values) else "") for i, h in enumerate(headers)}


def iter_labwin_rows(csv_path: Path, encoding: str = "utf-8-sig") -> Iterator[tuple[int, dict[str, str]]]:
    with csv_path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.reader(fh)
        raw_headers = next(reader)
        headers = uniquify_headers(raw_headers)
        for line_no, values in enumerate(reader, start=2):
            if not values or all(not (v or "").strip() for v in values):
                continue
            yield line_no, _row_dict(headers, values)


def load_labwin_csv(
    csv_path: Path,
    encoding: str = "utf-8-sig",
) -> tuple[dict[str, LabwinPatient], list[LabwinOrder], LabwinStats]:
    stats = LabwinStats()
    patients: dict[str, LabwinPatient] = {}
    orders: list[LabwinOrder] = []

    for line_no, row in iter_labwin_rows(csv_path, encoding=encoding):
        stats.lines_read += 1
        dni = normalize_dni(row.get("Nº doc."))
        if not dni:
            stats.dni_vacios += 1
            continue
        if dni in SKIP_DNI:
            stats.dni_omitidos_revision += 1
            continue
        if not DNI_RE.match(dni):
            stats.dni_invalidos += 1
            if len(stats.warnings) < 40:
                stats.warnings.append(
                    f"L{line_no}: DNI inválido {dni!r} ({row.get('Apellido y nombre', '')})"
                )
            continue

        fecha = parse_fecha(row.get("Fecha"))
        apellido, nombre = split_nombre(row.get("Apellido y nombre"))
        loc = (row.get("Localidad") or "").strip()
        telefono = telefono_desde_fila(row.get("Celular") or "", row.get("Teléfono") or "")
        if len(telefono) > 20:
            if len(stats.warnings) < 80:
                stats.warnings.append(f"L{line_no}: teléfono recortado a 20 ({dni})")
            telefono = telefono[:20]
        patient = LabwinPatient(
            dni=dni,
            apellido=apellido[:100],
            nombre=nombre[:100],
            telefono=telefono,
            direccion="" if is_empty(loc) else loc.upper(),
            fecha=fecha,
            source_line=line_no,
        )
        prev = patients.get(dni)
        if prev is None or (fecha and (prev.fecha is None or fecha >= prev.fecha)):
            patients[dni] = patient

        if fecha is None:
            if len(stats.warnings) < 80:
                stats.warnings.append(f"L{line_no}: fecha inválida, se omite la orden")
            continue

        numero = (row.get("Número") or "").strip()
        protocolo = format_protocolo_labwin(fecha, numero)
        if not protocolo:
            if len(stats.warnings) < 80:
                stats.warnings.append(f"L{line_no}: número LabWin inválido {numero!r}")
            continue

        resultados = _pick_resultados(row)
        paneles: list[str] = []
        eab = extraer_eab_layout_b(row)
        if eab:
            eab_res, panel = eab
            resultados.update(eab_res)
            paneles.append(panel)
            if panel == "PAN_EAB_ART":
                stats.eab_art += 1
            else:
                stats.eab_ven += 1
        else:
            ph_n = parse_valor_numerico(row.get("pH") or "")
            pco2_n = parse_valor_numerico(row.get("pCO2") or "")
            eb_n = parse_valor_numerico(row.get("Eb") or "")
            if eab_parece_layout_viejo(ph_n, pco2_n, eb_n):
                stats.eab_omitido_layout_viejo += 1

        if not resultados:
            stats.rows_sin_resultado += 1
            continue

        stats.rows_parsed += 1
        orders.append(
            LabwinOrder(
                dni=dni,
                fecha=fecha,
                numero_labwin=numero,
                protocolo=protocolo,
                resultados=resultados,
                paneles=paneles,
                source_line=line_no,
            )
        )

    stats.unique_patients = len(patients)
    stats.orders = len(orders)
    return patients, orders, stats
