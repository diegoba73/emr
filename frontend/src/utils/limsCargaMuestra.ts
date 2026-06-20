/**
 * Validación y payload para carga de resultados LIMS (B2-C).
 * Sin logs de datos sensibles.
 */
import type { CargarResultadoPayload, LimsTipoExamen, MuestraTransaccional, ResultadoExamenLims } from '../types/lims';

export const MUESTRA_ESTADOS_PROCESABLES = ['RECIBIDA', 'CONSERVADA', 'EN_PROCESO'] as const;

export type DraftCargaRow = {
  valor: string;
  valor_numerico: string;
  unidad: string;
  es_patologico: boolean;
  es_critico: boolean;
  observaciones: string;
  muestra_id: number | null;
};

export function isMuestraProcesable(estado: string): boolean {
  return (MUESTRA_ESTADOS_PROCESABLES as readonly string[]).includes(estado);
}

export function filterMuestrasProcesables(muestras: MuestraTransaccional[]): MuestraTransaccional[] {
  return muestras.filter((m) => isMuestraProcesable(m.estado));
}

export function muestrasCompatiblesParaTipo(
  procesables: MuestraTransaccional[],
  tipoMuestraRequeridaId: number | undefined
): MuestraTransaccional[] {
  if (!tipoMuestraRequeridaId) return procesables;
  return procesables.filter((m) => m.tipo_muestra === tipoMuestraRequeridaId);
}

export function getTipoExamenCatalog(
  tipoExamenId: number,
  catalog: Map<number, LimsTipoExamen>
): LimsTipoExamen | undefined {
  return catalog.get(tipoExamenId);
}

export function validateCargaResultadosMuestra(
  resultados: ResultadoExamenLims[],
  draft: Record<number, DraftCargaRow>,
  catalog: Map<number, LimsTipoExamen>,
  muestras: MuestraTransaccional[]
): string | null {
  for (const r of resultados) {
    const row = draft[r.id];
    if (!row) continue;
    const nombre = r.tipo_examen_nombre || String(r.tipo_examen);
    const te = catalog.get(r.tipo_examen);

    if (te?.requiere_muestra && row.muestra_id == null) {
      return `El examen ${nombre} requiere una muestra asociada.`;
    }

    if (row.muestra_id != null && te?.tipo_muestra_requerida != null) {
      const muestra = muestras.find((m) => m.id === row.muestra_id);
      if (muestra && muestra.tipo_muestra !== te.tipo_muestra_requerida) {
        return `La muestra seleccionada no corresponde al tipo requerido para ${nombre}.`;
      }
    }
  }
  return null;
}

export function parseValorNumerico(raw: string): number | string | undefined {
  const t = raw.trim();
  if (!t) return undefined;
  const n = Number(t);
  if (!Number.isNaN(n)) return n;
  return t;
}

export function buildCargarResultadoPayload(
  resultadoId: number,
  row: DraftCargaRow
): CargarResultadoPayload {
  let valor = row.valor.trim();
  const vnStr = row.valor_numerico.trim();
  if (!valor && vnStr) valor = vnStr;

  const item: CargarResultadoPayload = {
    id: resultadoId,
    valor,
    es_patologico: row.es_patologico,
    es_critico: row.es_critico,
    observaciones: row.observaciones ?? '',
  };

  const vn = parseValorNumerico(vnStr);
  if (vn !== undefined) item.valor_numerico = vn;

  const unidad = row.unidad.trim();
  if (unidad) item.unidad = unidad;

  if (row.muestra_id != null) {
    item.muestra_id = row.muestra_id;
  }

  return item;
}

export function formatMuestraSelectLabel(
  m: MuestraTransaccional,
  tipoMuestraNombre?: string
): string {
  const tipo = tipoMuestraNombre || `tipo #${m.tipo_muestra}`;
  const cont = m.tipo_contenedor != null ? ` · cont. #${m.tipo_contenedor}` : '';
  return `#${m.id} · ${tipo}${cont} · ${m.estado}`;
}
