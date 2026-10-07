#!/usr/bin/env bash
# Commit + push del trabajo LIMS pendiente (bandeja PENDIENTES, búsqueda por año, ENA/orden).
# Uso en WSL: bash scripts/sync_lims_bandeja_github.sh
set -euo pipefail
cd "$(dirname "$0")/.."

git status -sb

git add \
  frontend/src/pages/laboratorio/OrdenesLims.tsx \
  frontend/src/utils/limsBusquedaOrden.ts \
  frontend/src/utils/limsBusquedaOrden.test.ts \
  frontend/src/services/limsApi.ts \
  frontend/src/services/limsMicroApi.ts \
  frontend/src/modules/laboratorio/solicitudAnalisisPapelLayout.ts \
  frontend/src/utils/limsOrdenInforme.ts \
  frontend/src/utils/limsResultadosPanel.ts \
  frontend/src/utils/limsResultadosPanel.test.ts \
  laboratorio/views.py \
  laboratorio/views_microbiologia.py \
  laboratorio/calculos_derivados.py \
  laboratorio/catalogo_referencias_clinicas.py \
  laboratorio/catalogo_solicitud_papel.py \
  laboratorio/hemograma_resultados.py \
  laboratorio/informe_pdf_layout.py \
  laboratorio/orden_grupos_informe.py \
  laboratorio/solicitud_orden_abierta.py \
  laboratorio/tests/test_calculos_derivados.py \
  laboratorio/tests/test_clearance_calculado_api.py \
  laboratorio/tests/test_orden_grupos_informe.py \
  laboratorio/tests/test_seed_catalogo_solicitud_papel.py \
  laboratorio/tests/test_ena_panel.py \
  mobile/src/lib/ordenResultadosInforme.ts

if git diff --cached --quiet; then
  echo "Nada nuevo para commitear (¿ya estaba commiteado?)."
else
  git commit -m "$(cat <<'EOF'
LIMS: bandeja PENDIENTES, búsqueda por año y panel ENA

Pestaña PENDIENTES sin día, búsqueda 30=año curso / 2026-00030=exacto,
API cola/anio; panel ENA multipunto y orden de presentación clearance/orina.

EOF
)"
fi

git push origin master
git status -sb
git log -1 --oneline
echo
echo "Listo en GitHub. Para producción ver el chat / docs de despliegue."
