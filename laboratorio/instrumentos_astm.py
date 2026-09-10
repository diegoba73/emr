"""ASTM E1381 (sesión/frames) + E1394 (registros H/P/O/Q/R/L)."""
from __future__ import annotations

from dataclasses import dataclass

ENQ = b"\x05"
ACK = b"\x06"
NAK = b"\x15"
EOT = b"\x04"
STX = b"\x02"
ETX = b"\x03"
ETB = b"\x17"
CR = b"\x0d"
LF = b"\x0a"
CRLF = b"\r\n"


def checksum_hex(payload: bytes) -> bytes:
    """Suma módulo 256 de FN..ETX/ETB, dos caracteres ASCII hex mayúsculas."""
    total = sum(payload) & 0xFF
    return f"{total:02X}".encode("ascii")


def encode_frame(text: str, frame_number: int = 1, *, last: bool = True) -> bytes:
    fn = str(frame_number % 8).encode("ascii")
    body = text.encode("latin-1", errors="replace")
    end = ETX if last else ETB
    inner = fn + body + end
    return STX + inner + checksum_hex(inner) + CR + LF


def decode_frame(raw: bytes) -> str:
    if not raw.startswith(STX):
        raise ValueError("Frame ASTM sin STX")
    end_idx = raw.find(ETX)
    last = True
    if end_idx < 0:
        end_idx = raw.find(ETB)
        last = False
    if end_idx < 0:
        raise ValueError("Frame ASTM sin ETX/ETB")
    inner = raw[1 : end_idx + 1]
    cs_got = raw[end_idx + 1 : end_idx + 3]
    if checksum_hex(inner) != cs_got:
        raise ValueError("Checksum ASTM inválido")
    # inner = FN + text + ETX/ETB
    text = inner[1:-1].decode("latin-1", errors="replace")
    if last:
        return text.rstrip("\r")
    return text.rstrip("\r")


def split_records(message: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in message.replace("\r\n", "\r").split("\r"):
        line = line.strip("\n")
        if not line:
            continue
        rows.append(line.split("|"))
    return rows


def join_records(records: list[list[str]]) -> str:
    return "\r".join("|".join(str(c) for c in rec) for rec in records) + "\r"


def field(record: list[str], index: int, default: str = "") -> str:
    if index < len(record):
        return record[index]
    return default


def record_type(record: list[str]) -> str:
    if not record:
        return ""
    return (record[0] or "")[:1].upper()


def sample_id_from_query(records: list[list[str]]) -> str:
    """Q.2 suele ser ^sampleId o sampleId."""
    for rec in records:
        if record_type(rec) != "Q":
            continue
        raw = field(rec, 2)
        parts = [p for p in raw.split("^") if p]
        if parts:
            return parts[-1].strip()
        if raw.strip():
            return raw.strip()
    # A veces el ID va en O
    for rec in records:
        if record_type(rec) == "O":
            sid = field(rec, 2).split("^")[0].strip()
            if sid:
                return sid
    return ""


@dataclass
class ResultadoAstm:
    codigo: str
    valor: str
    unidad: str = ""


def _codigo_desde_universal(raw: str) -> str:
    """Campo R.2: ^^^WBC o ^^^WBC^1 → WBC."""
    parts = [p.strip().upper() for p in (raw or "").split("^") if p.strip()]
    return parts[0] if parts else ""


def parse_resultados(records: list[list[str]]) -> tuple[str, list[ResultadoAstm]]:
    sample_id = ""
    resultados: list[ResultadoAstm] = []
    for rec in records:
        kind = record_type(rec)
        if kind == "O":
            sample_id = field(rec, 2).split("^")[0].strip() or sample_id
        elif kind == "R":
            codigo = _codigo_desde_universal(field(rec, 2))
            valor = field(rec, 3).strip()
            unidad = field(rec, 4).strip()
            if codigo and valor:
                resultados.append(ResultadoAstm(codigo=codigo, valor=valor, unidad=unidad))
    if not sample_id:
        sample_id = sample_id_from_query(records)
    return sample_id, resultados


def build_header(sender: str = "SYNESIS") -> list[str]:
    return ["H", r"\^&", "", "", sender, "", "", "", "", "", "", "", "P", "1"]


def build_patient(*, sample_id: str, apellido: str, nombre: str, dni: str) -> list[str]:
    return ["P", "1", sample_id, dni, f"{apellido}^{nombre}"]


def build_order(*, seq: int, sample_id: str, test_codes: list[str]) -> list[str]:
    universal = "\\".join(f"^^^ {c}".replace(" ", "") for c in test_codes)
    return ["O", str(seq), sample_id, "", universal, "R"]


def build_terminator() -> list[str]:
    return ["L", "1", "N"]


def build_worklist_message(
    *,
    sample_id: str,
    apellido: str,
    nombre: str,
    dni: str,
    test_codes: list[str],
    sender: str = "SYNESIS",
) -> str:
    records = [
        build_header(sender),
        build_patient(sample_id=sample_id, apellido=apellido, nombre=nombre, dni=dni),
        build_order(seq=1, sample_id=sample_id, test_codes=test_codes),
        build_terminator(),
    ]
    return join_records(records)


def frames_from_message(message: str, *, max_len: int = 240) -> list[bytes]:
    chunks: list[str] = []
    rest = message
    while rest:
        chunks.append(rest[:max_len])
        rest = rest[max_len:]
    if not chunks:
        chunks = [""]
    out: list[bytes] = []
    for i, chunk in enumerate(chunks, start=1):
        out.append(encode_frame(chunk, frame_number=i, last=(i == len(chunks))))
    return out
