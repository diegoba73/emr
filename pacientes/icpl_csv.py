"""
Importación de fichas de paciente desde el CSV de internaciones ICPL.

El archivo ``PACIENTES.csv`` registra internaciones (una fila por ingreso).
Se deduplica por DNI conservando el ingreso más reciente y completando campos
vacíos con datos de filas anteriores del mismo paciente.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator

MES_ES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

MESES_HEADER = {
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
}

PHONE_SPLIT_RE = re.compile(r"[/|,]")
DNI_RE = re.compile(r"^\d{5,11}$")


@dataclass
class IcplPatientRow:
    numero_hc: str = ""
    fecha_ingreso: date | None = None
    apellido: str = ""
    nombre: str = ""
    telefono: str = ""
    dni: str = ""
    obra_social: str = ""
    numero_afiliado: str = ""
    fecha_nacimiento: date | None = None
    sexo: str = ""
    direccion: str = ""
    responsable: str = ""
    diagnostico: str = ""
    source_line: int = 0


@dataclass
class IcplImportStats:
    lines_read: int = 0
    rows_parsed: int = 0
    rows_skipped: int = 0
    unique_patients: int = 0
    warnings: list[str] = field(default_factory=list)


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def _title_name(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text.title()


def _normalize_dni(value: str) -> str:
    text = _clean(value).replace(".", "").replace(" ", "")
    if not text or not DNI_RE.match(text):
        return ""
    return text


def _parse_sexo(value: str) -> str:
    text = _clean(value).upper()
    if text in ("M", "F"):
        return text
    return ""


def _parse_spanish_month_token(token: str) -> int | None:
    key = token.strip().lower()[:3]
    return MES_ES.get(key)


def _parse_birth_date(value: str) -> date | None:
    text = _clean(value).lower().replace(" ", "")
    if not text:
        return None

    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            if parsed.year < 100:
                parsed = parsed.replace(year=parsed.year + 1900)
            return parsed
        except ValueError:
            continue

    m = re.match(r"^(\d{1,2})[-/]([a-z]{3,})$", text)
    if m:
        day = int(m.group(1))
        month = _parse_spanish_month_token(m.group(2))
        if month:
            return date(1900, month, day)

    m = re.match(r"^([a-z]{3,})[-/](\d{2,4})$", text)
    if m:
        month = _parse_spanish_month_token(m.group(1))
        if not month:
            return None
        year_raw = int(m.group(2))
        year = year_raw + 1900 if year_raw < 100 else year_raw
        return date(year, month, 1)

    return None


def _parse_admission_date(value: str) -> date | None:
    text = _clean(value).replace(".", "/")
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%b", "%d-%b-%Y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            if parsed.year < 100:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed
        except ValueError:
            continue
    return None


def _split_full_name(value: str) -> tuple[str, str]:
    text = _clean(value).upper()
    if not text:
        return "", ""

    if "," in text:
        apellido, _, nombre = text.partition(",")
        return _title_name(apellido), _title_name(nombre)

    parts = text.split()
    if len(parts) == 1:
        return _title_name(parts[0]), ""
    return _title_name(parts[0]), _title_name(" ".join(parts[1:]))


def _first_phone(value: str, *, max_len: int = 20) -> str:
    text = _clean(value)
    if not text:
        return ""
    for chunk in PHONE_SPLIT_RE.split(text):
        phone = re.sub(r"[^\d+]", "", chunk)
        if phone:
            return phone[:max_len]
    return re.sub(r"[^\d+]", "", text)[:max_len]


def _is_header_or_separator(row: list[str]) -> bool:
    if not row:
        return True
    first = _clean(row[0]).upper()
    if not first:
        return True
    if first in MESES_HEADER:
        return True
    if re.match(r"^[A-Z]{3,}-\d{2}$", first):
        return True
    if first.startswith("N°") or first == "INGRESO":
        return True
    return False


def _row_get(row: list[str], index: int) -> str:
    if index >= len(row):
        return ""
    return _clean(row[index])


def parse_icpl_csv_row(row: list[str], *, line_no: int) -> IcplPatientRow | None:
    if _is_header_or_separator(row):
        return None

    dni = _normalize_dni(_row_get(row, 5))
    if not dni:
        return None

    apellido, nombre = _split_full_name(_row_get(row, 3))
    if not apellido and not nombre:
        return None

    return IcplPatientRow(
        numero_hc=_row_get(row, 0),
        fecha_ingreso=_parse_admission_date(_row_get(row, 2)),
        apellido=apellido,
        nombre=nombre,
        telefono=_first_phone(_row_get(row, 4)),
        dni=dni,
        obra_social=_normalize_obra_social(_row_get(row, 6)),
        numero_afiliado=_row_get(row, 7)[:50],
        fecha_nacimiento=_parse_birth_date(_row_get(row, 8)),
        sexo=_parse_sexo(_row_get(row, 10)),
        direccion=_row_get(row, 13),
        responsable=_row_get(row, 12),
        diagnostico=_row_get(row, 11),
        source_line=line_no,
    )


def iter_icpl_patient_rows(
    source: Iterable[list[str]],
    *,
    start_line: int = 1,
) -> Iterator[IcplPatientRow]:
    for offset, row in enumerate(source):
        line_no = start_line + offset
        parsed = parse_icpl_csv_row(row, line_no=line_no)
        if parsed is not None:
            yield parsed


def _normalize_obra_social(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    # Unificar variantes frecuentes del legado ICPL.
    upper = text.upper()
    aliases = {
        "SEROS ": "SEROS",
        "SEROS  ": "SEROS",
        "OSPE": "OSPE",
        "OSDE": "OSDE",
        "PAMI": "PAMI",
        "MEDICUS": "MEDICUS",
        "SANCOR SALUD": "SANCOR SALUD",
        "PREVENCION SALUD": "PREVENCIÓN SALUD",
    }
    normalized = aliases.get(upper, text)
    return normalized[:100]


def _merge_patient(primary: IcplPatientRow, fallback: IcplPatientRow) -> IcplPatientRow:
    def pick(pref: str, alt: str) -> str:
        return pref if pref else alt

    def pick_date(pref: date | None, alt: date | None) -> date | None:
        return pref if pref else alt

    merged = IcplPatientRow(
        numero_hc=pick(primary.numero_hc, fallback.numero_hc),
        fecha_ingreso=primary.fecha_ingreso or fallback.fecha_ingreso,
        apellido=pick(primary.apellido, fallback.apellido),
        nombre=pick(primary.nombre, fallback.nombre),
        telefono=pick(primary.telefono, fallback.telefono),
        dni=primary.dni,
        obra_social=pick(primary.obra_social, fallback.obra_social),
        numero_afiliado=pick(primary.numero_afiliado, fallback.numero_afiliado),
        fecha_nacimiento=pick_date(primary.fecha_nacimiento, fallback.fecha_nacimiento),
        sexo=pick(primary.sexo, fallback.sexo),
        direccion=pick(primary.direccion, fallback.direccion),
        responsable=pick(primary.responsable, fallback.responsable),
        diagnostico=pick(primary.diagnostico, fallback.diagnostico),
        source_line=primary.source_line,
    )
    return merged


def dedupe_icpl_patients(rows: Iterable[IcplPatientRow]) -> tuple[dict[str, IcplPatientRow], list[str]]:
    patients: dict[str, IcplPatientRow] = {}
    warnings: list[str] = []

    for row in rows:
        current = patients.get(row.dni)
        if current is None:
            patients[row.dni] = row
            continue

        if (
            current.apellido
            and row.apellido
            and current.apellido.upper() != row.apellido.upper()
        ):
            warnings.append(
                f"DNI {row.dni}: apellido distinto "
                f"('{current.apellido}' vs '{row.apellido}'), línea {row.source_line}"
            )

        current_date = current.fecha_ingreso or date.min
        incoming_date = row.fecha_ingreso or date.min
        if incoming_date >= current_date:
            patients[row.dni] = _merge_patient(row, current)
        else:
            patients[row.dni] = _merge_patient(current, row)

    return patients, warnings


def load_icpl_patients_from_csv(
    csv_path: Path,
    *,
    encoding: str = "latin-1",
) -> tuple[dict[str, IcplPatientRow], IcplImportStats]:
    stats = IcplImportStats()
    parsed_rows: list[IcplPatientRow] = []

    with csv_path.open(newline="", encoding=encoding, errors="replace") as handle:
        reader = csv.reader(handle, delimiter=";")
        for line_no, row in enumerate(reader, start=1):
            stats.lines_read += 1
            if not any(_clean(cell) for cell in row):
                stats.rows_skipped += 1
                continue
            parsed = parse_icpl_csv_row(row, line_no=line_no)
            if parsed is None:
                stats.rows_skipped += 1
                continue
            parsed_rows.append(parsed)
            stats.rows_parsed += 1

    patients, warnings = dedupe_icpl_patients(parsed_rows)
    stats.unique_patients = len(patients)
    stats.warnings = warnings[:50]
    if len(warnings) > 50:
        stats.warnings.append(f"... y {len(warnings) - 50} advertencias más")
    return patients, stats


def summarize_icpl_coverage(patients: dict[str, IcplPatientRow]) -> dict[str, object]:
    from collections import Counter

    with_obra = sum(1 for row in patients.values() if row.obra_social)
    with_afiliado = sum(1 for row in patients.values() if row.numero_afiliado)
    obras = Counter(row.obra_social for row in patients.values() if row.obra_social)
    return {
        "with_obra_social": with_obra,
        "with_numero_afiliado": with_afiliado,
        "top_obras_sociales": obras.most_common(8),
    }


def build_observaciones(row: IcplPatientRow) -> str:
    parts = ["Importado desde PACIENTES.csv (ICPL)."]
    if row.numero_hc:
        parts.append(f"HC: {row.numero_hc}.")
    if row.responsable:
        parts.append(f"Responsable: {row.responsable}.")
    return " ".join(parts)
