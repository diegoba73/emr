"""LabWin micro catalog CSV reader (LEEME-compatible).

LEEME: UTF-8, comma separator, double-quote, headers.
NULL = empty field WITHOUT quotes -> None
Empty string = quoted "" -> ""
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, TextIO


def cell_str(value: Any) -> str:
    """Normalize a CSV cell to str; None/blank -> empty string."""
    if value is None:
        return ""
    return str(value).strip() if isinstance(value, str) else str(value)


def _parse_labwin_record(text: str, start: int) -> tuple[list[Any], int]:
    """Parse one CSV record starting at index ``start``. Returns (fields, next_index)."""
    n = len(text)
    i = start
    fields: list[Any] = []
    field_chars: list[str] = []
    in_quotes = False
    field_quoted = False

    def end_field() -> None:
        nonlocal field_chars, field_quoted
        if not field_chars and not field_quoted:
            fields.append(None)
        else:
            fields.append("".join(field_chars))
        field_chars = []
        field_quoted = False

    while i < n:
        ch = text[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field_chars.append('"')
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue
            field_chars.append(ch)
            i += 1
            continue

        if ch == '"':
            in_quotes = True
            field_quoted = True
            i += 1
            continue
        if ch == ",":
            end_field()
            i += 1
            continue
        if ch == "\r":
            i += 1
            continue
        if ch == "\n":
            end_field()
            i += 1
            break
        field_chars.append(ch)
        i += 1
    else:
        if field_chars or field_quoted or (fields and text[start:i].endswith(",")):
            end_field()
        elif not fields and start < n:
            end_field()

    return fields, i


def iter_labwin_csv_rows(path: str | Path, *, encoding: str = "utf-8") -> Iterator[dict[str, Any]]:
    """Yield dict rows; unquoted empty -> None, quoted empty -> \"\"."""
    path = Path(path)
    text = path.read_text(encoding=encoding)
    if text.startswith("\ufeff"):
        text = text[1:]
    i = 0
    n = len(text)
    if n == 0:
        return
    header_fields, i = _parse_labwin_record(text, 0)
    headers = [str(h) if h is not None else "" for h in header_fields]
    while i < n:
        if text[i] in "\r\n":
            i += 1
            continue
        values, i = _parse_labwin_record(text, i)
        if not values and i >= n:
            break
        row: dict[str, Any] = {}
        for idx, name in enumerate(headers):
            row[name] = values[idx] if idx < len(values) else None
        yield row


def iter_labwin_csv(path: str | Path, *, encoding: str = "utf-8") -> Iterator[dict[str, Any]]:
    """Alias of ``iter_labwin_csv_rows``."""
    yield from iter_labwin_csv_rows(path, encoding=encoding)


def read_labwin_csv(path: str | Path, *, encoding: str = "utf-8") -> list[dict[str, Any]]:
    return list(iter_labwin_csv_rows(path, encoding=encoding))
