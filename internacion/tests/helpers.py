"""Helpers para tests de internación con datos únicos e idempotentes."""
from __future__ import annotations

import uuid


def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


def unique_cie10_code(prefix: str = "T") -> str:
    """Código CIE-10 único respetando ``DiagnosticoCIE10.codigo`` max_length=10."""
    head = (prefix or "T")[:1]
    tail_len = 10 - len(head)
    return f"{head}{uuid.uuid4().hex[:tail_len]}"
