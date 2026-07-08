"""
Importación de médicos ICPL / CEHTA Trelew desde CSV estructurado.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ESPECIALIDAD_ALIASES: dict[str, str] = {
    "cardiologia intervencionista": "Cardiología",
    "residencia en cardiologia clinica": "Cardiología",
    "clinica medica": "Clínica médica",
    "cirugia cardiovascular": "Cirugía cardiovascular",
    "cirugia general": "Cirugía general",
    "no verificada": "",
}


@dataclass
class IcplMedicoRow:
    import_id: str = ""
    institucion_codigo: str = ""
    institucion_nombre: str = ""
    sede_nombre: str = ""
    direccion: str = ""
    localidad: str = ""
    apellido: str = ""
    nombres: str = ""
    titulo_tratamiento: str = ""
    especialidad_principal: str = ""
    subespecialidades: str = ""
    servicio_area: str = ""
    cargo_rol: str = ""
    tipo_vinculo: str = ""
    horario_consultorio: str = ""
    matricula_profesional: str = ""
    activo_sugerido: bool = True
    estado_verificacion: str = ""
    observaciones: str = ""
    source_line: int = 0

    @property
    def dedupe_key(self) -> str:
        return f"{_normalize_key(self.apellido)}|{_normalize_key(self.nombres)}"


@dataclass
class IcplMedicoImportStats:
    lines_read: int = 0
    rows_parsed: int = 0
    rows_skipped: int = 0
    unique_medicos: int = 0
    especialidades_detectadas: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def _normalize_key(value: str) -> str:
    text = _clean(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def _title_name(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text.title()


def _parse_bool(value: str) -> bool:
    text = _clean(value).lower()
    return text in {"1", "true", "si", "sí", "yes"}


def _normalize_matricula(value: str, *, import_id: str) -> str:
    text = _clean(value)
    if text:
        text = re.sub(r"\s+", " ", text.upper())
        return text[:50]
    if import_id:
        return import_id.replace(" ", "-")[:50]
    return ""


def canonical_especialidad_nombre(value: str) -> str | None:
    text = _clean(value)
    if not text:
        return None
    key = _normalize_key(text)
    if key in ESPECIALIDAD_ALIASES:
        mapped = ESPECIALIDAD_ALIASES[key]
        return mapped or None
    return text


def parse_icpl_medico_row(row: dict[str, str], *, line_no: int) -> IcplMedicoRow | None:
    import_id = _clean(row.get("import_id"))
    apellido = _title_name(row.get("apellido", ""))
    nombres = _title_name(row.get("nombres", ""))
    if not apellido and not nombres:
        return None

    return IcplMedicoRow(
        import_id=import_id,
        institucion_codigo=_clean(row.get("institucion_codigo")),
        institucion_nombre=_clean(row.get("institucion_nombre")),
        sede_nombre=_clean(row.get("sede_nombre")),
        direccion=_clean(row.get("direccion")),
        localidad=_clean(row.get("localidad")),
        apellido=apellido,
        nombres=nombres,
        titulo_tratamiento=_clean(row.get("titulo_tratamiento")),
        especialidad_principal=_clean(row.get("especialidad_principal")),
        subespecialidades=_clean(row.get("subespecialidades")),
        servicio_area=_clean(row.get("servicio_area")),
        cargo_rol=_clean(row.get("cargo_rol")),
        tipo_vinculo=_clean(row.get("tipo_vinculo")),
        horario_consultorio=_clean(row.get("horario_consultorio")),
        matricula_profesional=_clean(row.get("matricula_profesional")),
        activo_sugerido=_parse_bool(row.get("activo_sugerido", "1")),
        estado_verificacion=_clean(row.get("estado_verificacion")),
        observaciones=_clean(row.get("observaciones")),
        source_line=line_no,
    )


def _merge_medico(primary: IcplMedicoRow, fallback: IcplMedicoRow) -> IcplMedicoRow:
    def pick(pref: str, alt: str) -> str:
        return pref if pref else alt

    instituciones = {
        code
        for code in (primary.institucion_codigo, fallback.institucion_codigo)
        if code
    }
    institucion_codigo = "/".join(sorted(instituciones))

    matricula = primary.matricula_profesional or fallback.matricula_profesional
    import_id = primary.import_id or fallback.import_id

    return IcplMedicoRow(
        import_id=import_id,
        institucion_codigo=institucion_codigo,
        institucion_nombre=pick(primary.institucion_nombre, fallback.institucion_nombre),
        sede_nombre=pick(primary.sede_nombre, fallback.sede_nombre),
        direccion=pick(primary.direccion, fallback.direccion),
        localidad=pick(primary.localidad, fallback.localidad),
        apellido=pick(primary.apellido, fallback.apellido),
        nombres=pick(primary.nombres, fallback.nombres),
        titulo_tratamiento=pick(primary.titulo_tratamiento, fallback.titulo_tratamiento),
        especialidad_principal=pick(primary.especialidad_principal, fallback.especialidad_principal),
        subespecialidades=_join_unique(primary.subespecialidades, fallback.subespecialidades),
        servicio_area=pick(primary.servicio_area, fallback.servicio_area),
        cargo_rol=_join_unique(primary.cargo_rol, fallback.cargo_rol),
        tipo_vinculo=_join_unique(primary.tipo_vinculo, fallback.tipo_vinculo),
        horario_consultorio=pick(primary.horario_consultorio, fallback.horario_consultorio),
        matricula_profesional=matricula,
        activo_sugerido=primary.activo_sugerido or fallback.activo_sugerido,
        estado_verificacion=pick(primary.estado_verificacion, fallback.estado_verificacion),
        observaciones=_join_unique(primary.observaciones, fallback.observaciones, sep=" | "),
        source_line=primary.source_line,
    )


def _join_unique(*values: str, sep: str = "; ") -> str:
    seen: list[str] = []
    for value in values:
        for chunk in re.split(r"[;|]", value or ""):
            item = _clean(chunk)
            if item and item not in seen:
                seen.append(item)
    return sep.join(seen)


def dedupe_icpl_medicos(rows: Iterable[IcplMedicoRow]) -> tuple[dict[str, IcplMedicoRow], list[str]]:
    medicos: dict[str, IcplMedicoRow] = {}
    warnings: list[str] = []

    for row in rows:
        key = row.dedupe_key
        if not key or key == "|":
            continue
        current = medicos.get(key)
        if current is None:
            medicos[key] = row
            continue

        if current.matricula_profesional and row.matricula_profesional:
            if _normalize_key(current.matricula_profesional) != _normalize_key(row.matricula_profesional):
                warnings.append(
                    f"{row.apellido}, {row.nombres}: matrículas distintas "
                    f"({current.matricula_profesional} vs {row.matricula_profesional}), línea {row.source_line}"
                )

        prefer = row if len(row.institucion_codigo) >= len(current.institucion_codigo) else current
        other = current if prefer is row else row
        medicos[key] = _merge_medico(prefer, other)

    return medicos, warnings


def load_icpl_medicos_from_csv(
    csv_path: Path,
    *,
    encoding: str = "utf-8-sig",
) -> tuple[dict[str, IcplMedicoRow], IcplMedicoImportStats]:
    stats = IcplMedicoImportStats()
    parsed_rows: list[IcplMedicoRow] = []

    with csv_path.open(newline="", encoding=encoding, errors="replace") as handle:
        reader = csv.DictReader(handle)
        for line_no, row in enumerate(reader, start=2):
            stats.lines_read += 1
            parsed = parse_icpl_medico_row(row, line_no=line_no)
            if parsed is None:
                stats.rows_skipped += 1
                continue
            parsed_rows.append(parsed)
            stats.rows_parsed += 1
            canon = canonical_especialidad_nombre(parsed.especialidad_principal)
            if canon:
                stats.especialidades_detectadas.add(canon)

    medicos, warnings = dedupe_icpl_medicos(parsed_rows)
    stats.unique_medicos = len(medicos)
    stats.warnings = warnings[:30]
    if len(warnings) > 30:
        stats.warnings.append(f"... y {len(warnings) - 30} advertencias más")
    return medicos, stats


def build_areas_interes(row: IcplMedicoRow) -> str:
    parts = [
        "Importado ICPL/CEHTA Trelew.",
        f"Instituciones: {row.institucion_codigo or '—'}.",
    ]
    if row.subespecialidades:
        parts.append(f"Subespecialidades: {row.subespecialidades}.")
    if row.servicio_area:
        parts.append(f"Servicio/área: {row.servicio_area}.")
    if row.cargo_rol:
        parts.append(f"Cargo: {row.cargo_rol}.")
    if row.tipo_vinculo:
        parts.append(f"Vínculo: {row.tipo_vinculo}.")
    if row.horario_consultorio:
        parts.append(f"Horario: {row.horario_consultorio}.")
    if row.sede_nombre:
        parts.append(f"Sede: {row.sede_nombre}.")
    if row.direccion:
        parts.append(f"Dirección: {row.direccion}, {row.localidad}.")
    if row.estado_verificacion:
        parts.append(f"Estado: {row.estado_verificacion}.")
    if not row.activo_sugerido:
        parts.append("Activo sugerido: no.")
    if row.observaciones:
        parts.append(f"Obs: {row.observaciones}")
    return " ".join(parts)
