#!/usr/bin/env python3
"""Genera frontend/src/assets/qrSynesisMovilDataUri.ts desde el PNG del QR."""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / "frontend" / "src" / "assets" / "qr-synesis-movil.png"
OUT = ROOT / "frontend" / "src" / "assets" / "qrSynesisMovilDataUri.ts"

def main() -> None:
    raw = PNG.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    uri = f"data:image/png;base64,{b64}"
    OUT.write_text(
        "/** QR de instalación SYNESIS (data URI). Generado por scripts/embed_movil_qr_data_uri.py */\n"
        f"const QR_SYNESIS_MOVIL_DATA_URI =\n  '{uri}';\n\n"
        "export default QR_SYNESIS_MOVIL_DATA_URI;\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({len(uri)} chars)")

if __name__ == "__main__":
    main()
