#!/usr/bin/env bash
# Empaqueta el agente USB de etiquetas para copiar a la PC LABORATORIO.
# SoT de scripts: scripts/label_print_agent* + EmrRawPrinter.cs
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts"
OUT_DIR="$ROOT/deploy/label_print_agent"
ZIP_OUT="${1:-/opt/cursor/artifacts/label_print_agent.zip}"

mkdir -p "$OUT_DIR"

FILES=(
  EmrRawPrinter.cs
  label_print_agent.ps1
  label_print_agent.bat
  label_print_agent_instalar.bat
  label_print_agent_install.ps1
  label_print_agent_reparar.bat
  label_print_agent_reparar.ps1
  label_print_agent_desinstalar.bat
  label_print_agent_desinstalar.ps1
  label_print_agent_listar_impresoras.bat
  label_print_agent.config.json.example
)

for f in "${FILES[@]}"; do
  if [[ ! -f "$SRC/$f" ]]; then
    echo "Falta $SRC/$f" >&2
    exit 1
  fi
  cp -f "$SRC/$f" "$OUT_DIR/$f"
done

# Config lista para usar: printerName vacío = auto-detect
cp -f "$SRC/label_print_agent.config.json.example" "$OUT_DIR/label_print_agent.config.json"

cat > "$OUT_DIR/LEEME_INSTALACION.txt" <<'EOF'
================================================================================
SYNESIS / EMR — Restaurar impresora de etiquetas (PC LABORATORIO)
================================================================================

La impresora NO se configura en el servidor. Va en la PC donde está el USB.

Destino recomendado en Windows:
  C:\EMR\label_print_agent\

--------------------------------------------------------------------------------
PASOS (primera vez o si se borró todo)
--------------------------------------------------------------------------------

1) Conectar la etiquetadora por USB e instalar el driver Windows
   (4BARCODE / TSPL, o Generic / Text Only si usan "EMR ZPL RAW").
   Rollo: 40 x 23 mm. Calibrar sensor gap/black mark.

2) Copiar TODO el contenido de esta carpeta a:
   C:\EMR\label_print_agent\

3) (Opcional) Ver el nombre exacto de la impresora en Windows:
   doble clic en label_print_agent_listar_impresoras.bat

   Si el nombre NO contiene alguno de:
     4BARCODE | 4B-2054 | EMR ZPL RAW | 3nStar | LDT114 | ZDesigner
   entonces editar label_print_agent.config.json y poner ese nombre en:
     "printerName": "NOMBRE EXACTO"

   Si sí coincide, dejar "printerName": "" (auto-detect).

4) Ejecutar UNA vez (usuario de LABORATORIO):
     label_print_agent_instalar.bat

   Eso registra la tarea de Windows y arranca el agente oculto en
   http://127.0.0.1:18181  (se inicia solo al iniciar sesión).

5) Abrir el EMR en el navegador DE ESA MISMA PC, por ejemplo:
     https://emr.sytes.net:8080
     http://192.168.10.240
   e imprimir una etiqueta de prueba (muestra o microbiología).

6) Si no imprime:
     - correr label_print_agent_reparar.bat
     - mirar label_print_agent.log en esta misma carpeta
     - confirmar que Windows ve la impresora (paso 3)

--------------------------------------------------------------------------------
ACTUALIZAR archivos del agente (sin reinstalar la tarea)
--------------------------------------------------------------------------------

1) Copiar encima los .ps1 / .bat / EmrRawPrinter.cs nuevos.
2) Ejecutar label_print_agent_reparar.bat  (no alcanza solo label_print_agent.bat
   si el puerto 18181 ya estaba ocupado).

--------------------------------------------------------------------------------
QUITAR
--------------------------------------------------------------------------------

  label_print_agent_desinstalar.bat

Detalle técnico: docs/labels-lims-3nstar-ldt114.md (en el repo EMR).
EOF

mkdir -p "$(dirname "$ZIP_OUT")"
rm -f "$ZIP_OUT"
(
  cd "$OUT_DIR"
  zip -r -q "$ZIP_OUT" .
)

echo "Paquete listo:"
echo "  carpeta: $OUT_DIR"
echo "  zip:     $ZIP_OUT"
ls -la "$OUT_DIR"
ls -la "$ZIP_OUT"
