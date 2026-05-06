"""
Sanitización y truncamiento de payloads JSON para auditoría.

Objetivos:
- evitar persistir secretos/credenciales/tokens conocidos por nombre de clave
- limitar tamaño de strings y profundidad de estructuras anidadas (metadata del usuario)
- no intentar auditoría exhaustiva tipo DLP — capa práctica minimalista.
"""
from __future__ import annotations

import json
import re
from typing import Any

# Claves típicamente sensibles (case-insensitive).
_SENSITIVE_SUBSTRINGS_RE = re.compile(
    r"(password|passwd|pwd|secret|token|jwt|csrf|csrftoken|authorization|cookie|"
    r"api[_-]?key|refresh|bearer|session|credential|private[_-]?key)",
    re.IGNORECASE,
)

_DEFAULT_MAX_DEPTH = 8
_DEFAULT_MAX_JSON_BYTES = 400_000  # ~390 KiB antes de Postgres JSONB (tunable)
_TRUNC_MARK = "...<truncado>"


def _should_redact_key(key: str) -> bool:
    return bool(key and _SENSITIVE_SUBSTRINGS_RE.search(key))


def sanitize_dict_keys(obj: Any, *, depth: int = 0, max_depth: int = _DEFAULT_MAX_DEPTH) -> Any:
    """
    Recorre dict/list y reemplaza valores cuyas claves parecen sensibles.
    También trunca strings largos en nivel de hoja (no cuenta bytes UTF-8 exactos por simplicidad).
    """
    if depth > max_depth:
        return _TRUNC_MARK
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        if len(obj) > 8192:
            return obj[:4096] + _TRUNC_MARK
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = str(k)
            if _should_redact_key(ks):
                out[ks] = "<redacted>"
            else:
                out[ks] = sanitize_dict_keys(v, depth=depth + 1, max_depth=max_depth)
        return out
    if isinstance(obj, (list, tuple)):
        return [sanitize_dict_keys(v, depth=depth + 1, max_depth=max_depth) for v in obj]
    return str(obj)


def _aggressive_trim_for_size(obj: Any, *, leaf_max: int = 2048) -> Any:
    """Recorta strings grandes y colecciones (último recurso antes del stub textual)."""

    def _leaf(s: Any) -> Any:
        if isinstance(s, str) and len(s) > leaf_max:
            return s[: leaf_max // 2] + _TRUNC_MARK
        return s

    if isinstance(obj, dict):
        out = {}
        for k, v in list(obj.items())[:80]:
            out[str(k)] = _aggressive_trim_for_size(v, leaf_max=leaf_max)
        out.setdefault("__size_trim__", True)
        return out
    if isinstance(obj, (list, tuple)):
        return [_aggressive_trim_for_size(v, leaf_max=leaf_max) for v in list(obj)[:120]]
    return _leaf(obj)


def enforce_max_json_payload(obj: Any, *, max_json_bytes: int = _DEFAULT_MAX_JSON_BYTES) -> Any:
    """
    Garantiza que el objeto serializado a JSON no exceda ``max_json_bytes``
    mediante recorte agresivo y, como último recurso, mensaje estable.
    """
    try:
        raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False, default=str)
    except Exception:
        return {"error": "<unserializable payload>"}

    if len(raw.encode("utf-8")) <= max_json_bytes:
        return obj

    trimmed = _aggressive_trim_for_size(obj)
    try:
        raw2 = json.dumps(trimmed, separators=(",", ":"), ensure_ascii=False, default=str)
    except Exception:
        trimmed = {"error": "<unserializable after trim>"}
        raw2 = json.dumps(trimmed)

    if len(raw2.encode("utf-8")) <= max_json_bytes:
        return trimmed

    stub = "<payload demasiado grande; truncado en enforce_max_json_payload>"
    return stub if len(json.dumps(stub).encode("utf-8")) <= max_json_bytes else "<truncado>"
