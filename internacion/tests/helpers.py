"""Helpers para tests de internación con datos únicos e idempotentes."""
from __future__ import annotations

import uuid


def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]
