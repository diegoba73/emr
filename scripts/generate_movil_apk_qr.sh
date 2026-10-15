#!/usr/bin/env bash
# Regenera las imágenes QR de instalación apuntando a la URL fija del APK.
# No hace falta regenerarlas al publicar una versión nueva: la URL no cambia.
#
#   bash scripts/generate_movil_apk_qr.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL='https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk'
VENV="${TMPDIR:-/tmp}/synesis-qrvenv"

python3 -m venv "$VENV"
"$VENV/bin/pip" -q install 'qrcode[pil]'
"$VENV/bin/python" - <<PY
import qrcode
from pathlib import Path
url = "$URL"
root = Path(r"$ROOT")
paths = [
    root / "frontend/public/qr-synesis-movil.png",
    root / "frontend/src/assets/qr-synesis-movil.png",  # importado por Login.tsx
    root / "mobile/assets/qr-instalacion-synesis-movil.png",
]
for p in paths:
    img = qrcode.make(url, box_size=12, border=2)
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p)
    p.chmod(0o644)  # nginx del contenedor debe poder leerlo (evitar 403)
    print(f"wrote {p} mode={oct(p.stat().st_mode & 0o777)} -> {url}")
PY
# Mantener el data URI del Login alineado con el PNG.
python3 "$ROOT/scripts/embed_movil_qr_data_uri.py"
