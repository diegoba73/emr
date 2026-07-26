"""Motor Westgard multi-regla."""
from __future__ import annotations

from typing import Any


def evaluate_punto(
    valor: float,
    mean: float,
    sd: float,
    previous_puntos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evalúa un punto QC.

    previous_puntos: lista de dicts con keys valor, z (más reciente al final).
    """
    previous_puntos = previous_puntos or []
    if sd is None or float(sd) == 0:
        return {
            "z": None,
            "rules": ["SD_CERO"],
            "fuera_control": True,
            "warning": False,
        }

    z = (float(valor) - float(mean)) / float(sd)
    rules: list[str] = []
    warning = False
    fuera = False

    abs_z = abs(z)
    if abs_z >= 3:
        rules.append("1-3s")
        fuera = True
    elif abs_z >= 2:
        rules.append("1-2s")
        warning = True

    hist = list(previous_puntos) + [{"valor": float(valor), "z": z}]
    zs = [p.get("z") for p in hist if p.get("z") is not None]

    # 2-2s: last two same side beyond 2s
    if len(zs) >= 2 and abs(zs[-1]) >= 2 and abs(zs[-2]) >= 2 and (zs[-1] * zs[-2] > 0):
        rules.append("2-2s")
        fuera = True

    # R-4s: range between last two >= 4s
    if len(zs) >= 2 and abs(zs[-1] - zs[-2]) >= 4:
        rules.append("R-4s")
        fuera = True

    # 4-1s: last 4 on same side beyond 1s
    if len(zs) >= 4:
        last4 = zs[-4:]
        if all(abs(x) >= 1 for x in last4) and all(x * last4[0] > 0 for x in last4):
            rules.append("4-1s")
            fuera = True

    # 10-x: last 10 on same side of mean
    if len(zs) >= 10:
        last10 = zs[-10:]
        if all(x * last10[0] > 0 for x in last10):
            rules.append("10-x")
            fuera = True

    # Deduplicate preserving order
    seen = set()
    uniq = []
    for r in rules:
        if r not in seen:
            seen.add(r)
            uniq.append(r)

    return {
        "z": round(z, 4),
        "rules": uniq,
        "fuera_control": fuera,
        "warning": warning and not fuera,
    }
