"""
Perfiles físicos de impresoras de etiquetas LIMS.

Acotado a 3nStar LDT114 / 40×23 mm / 203 dpi / ZPL.
No es un framework genérico de impresoras.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelPrinterProfile:
    key: str
    printer_name: str
    language: str
    dpi: int
    width_mm: int
    height_mm: int
    width_dots: int
    height_dots: int
    encoding_cmd: str  # p.ej. ^CI28 (UTF-8)


PROFILE_3NSTAR_LDT114_203_40X23 = LabelPrinterProfile(
    key="3nstar_ldt114_203_40x23",
    printer_name="3nStar LDT114",
    language="ZPL",
    dpi=203,
    width_mm=40,
    height_mm=23,
    width_dots=320,
    height_dots=184,
    encoding_cmd="^CI28",
)

LABEL_PROFILES: dict[str, LabelPrinterProfile] = {
    PROFILE_3NSTAR_LDT114_203_40X23.key: PROFILE_3NSTAR_LDT114_203_40X23,
}

DEFAULT_LABEL_PROFILE_KEY = PROFILE_3NSTAR_LDT114_203_40X23.key


def get_label_profile(key: str | None = None) -> LabelPrinterProfile:
    k = (key or DEFAULT_LABEL_PROFILE_KEY).strip() or DEFAULT_LABEL_PROFILE_KEY
    if k not in LABEL_PROFILES:
        raise ValueError(f"Perfil de impresora desconocido: {k}")
    return LABEL_PROFILES[k]
