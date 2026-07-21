/**
 * Validación y payload para carga de resultados LIMS (B2-C).
 * Sin logs de datos sensibles.
 */
import type { CargarResultadoPayload, LimsTipoExamen, MuestraTransaccional, ResultadoExamenLims } from '../types/lims';
import { convertTicketEntry, entryFromStored, usesTicketEntry } from './entradaResultados';
import { getSysmexUnidad } from './sysmexHemograma';

export const MUESTRA_ESTADOS_PROCESABLES = ['TOMADA', 'RECIBIDA', 'CONSERVADA', 'EN_PROCESO'] as const;

export type DraftCargaRow = {
  valor: string;
  /** Entero tal como sale en el ticket Sysmex (hemograma). */
  valor_sysmex: string;
  valor_numerico: string;
  unidad: string;
  muestra_id: number | null;
};

export function normalizeDraftRow(row?: Partial<DraftCargaRow> | null): DraftCargaRow {
  return {
    valor: row?.valor ?? '',
    valor_sysmex: row?.valor_sysmex ?? '',
    valor_numerico: row?.valor_numerico ?? '',
    unidad: row?.unidad ?? '',
    muestra_id: row?.muestra_id ?? null,
  };
}

export function isMuestraProcesable(estado: string): boolean {
  return (MUESTRA_ESTADOS_PROCESABLES as readonly string[]).includes(estado);
}

export function filterMuestrasProcesables(muestras: MuestraTransaccional[]): MuestraTransaccional[] {
  return muestras.filter((m) => isMuestraProcesable(m.estado));
}

export function muestrasCompatiblesParaTipo(
  procesables: MuestraTransaccional[],
  tipoMuestraRequeridaId: number | undefined,
  tipoContenedorId?: number | null
): MuestraTransaccional[] {
  if (tipoContenedorId != null) {
    const byCont = procesables.filter((m) => m.tipo_contenedor === tipoContenedorId);
    if (byCont.length > 0) return byCont;
  }
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
  muestras: MuestraTransaccional[],
  soloIds?: number[]
): string | null {
  for (const r of resultados) {
    if (soloIds && !soloIds.includes(r.id)) continue;
    const row = draft[r.id];
    if (!row) continue;
    const safe = normalizeDraftRow(row);
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

export function draftRowHasValue(
  row: DraftCargaRow,
  te?: LimsTipoExamen | null,
  codigo?: string | null
): boolean {
  const c = te?.codigo ?? codigo ?? '';
  if (usesTicketEntry(te, c)) {
    return !!row.valor_sysmex.trim();
  }
  return !!(row.valor.trim() || row.valor_numerico.trim());
}

export function validateCargaResultadosValores(
  resultados: ResultadoExamenLims[],
  draft: Record<number, DraftCargaRow>,
  catalog: Map<number, LimsTipoExamen>,
  soloIds: number[]
): string | null {
  for (const r of resultados) {
    if (!soloIds.includes(r.id)) continue;
    const row = draft[r.id];
    if (!row) continue;
    const safe = normalizeDraftRow(row);
    const te = catalog.get(r.tipo_examen);
    const codigo = r.tipo_examen_codigo ?? te?.codigo;
    const nombre = r.tipo_examen_nombre || codigo || String(r.tipo_examen);
    if (usesTicketEntry(te, codigo)) {
      const raw = safe.valor_sysmex.trim();
      if (raw && !convertTicketEntry(te, raw, codigo)) {
        return `${nombre}: valor de ticket inválido. Ingresá solo dígitos, sin punto decimal.`;
      }
    } else if (!safe.valor.trim() && !safe.valor_numerico.trim()) {
      return `${nombre}: ingresá un valor.`;
    }
  }
  return null;
}

export function buildCargarResultadoPayload(
  resultadoId: number,
  row: DraftCargaRow,
  te?: LimsTipoExamen | null,
  tipoExamenCodigo?: string | null
): CargarResultadoPayload {
  const codigo = te?.codigo ?? tipoExamenCodigo?.trim().toUpperCase() ?? '';
  const ticketEntry = usesTicketEntry(te, codigo);
  const ticketRaw = row.valor_sysmex.trim();

  if (ticketEntry && ticketRaw) {
    const conv = convertTicketEntry(te, ticketRaw, codigo);
    const item: CargarResultadoPayload = {
      id: resultadoId,
      valor: conv?.valorInforme ?? '',
      valor_sysmex: ticketRaw,
    };
    if (conv) {
      item.valor_numerico = Math.round(conv.valorNumerico * 10000) / 10000;
    }
    const unidad = row.unidad.trim() || te?.unidad_default?.trim() || getSysmexUnidad(codigo);
    if (unidad) item.unidad = unidad;
    if (row.muestra_id != null) item.muestra_id = row.muestra_id;
    return item;
  }

  let valor = row.valor.trim();
  const vnStr = row.valor_numerico.trim();
  if (!valor && vnStr) valor = vnStr;

  const item: CargarResultadoPayload = {
    id: resultadoId,
    valor,
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

export function draftSysmexTicketFromResultado(
  r: ResultadoExamenLims,
  te?: LimsTipoExamen | null,
  codigo?: string | null
): string {
  const c = te?.codigo ?? codigo ?? r.tipo_examen_codigo;
  if (!usesTicketEntry(te, c)) return '';
  const fromNumeric = entryFromStored(te, r.valor_numerico, c ?? '');
  if (fromNumeric) return fromNumeric;
  const raw = (r.valor_obtenido ?? '').trim();
  if (/^\d+$/.test(raw)) return raw;
  return '';
}

export function suggestMuestraIdForResultado(
  r: ResultadoExamenLims,
  procesables: MuestraTransaccional[],
  catalog: Map<number, LimsTipoExamen>,
  currentMuestraId: number | null
): number | null {
  if (currentMuestraId != null) return currentMuestraId;
  const te = catalog.get(r.tipo_examen);
  const opciones = muestrasCompatiblesParaTipo(
    procesables,
    te?.tipo_muestra_requerida,
    te?.tipo_contenedor
  );
  if (opciones.length === 1) return opciones[0].id;
  if (te?.requiere_muestra && opciones.length > 0) return opciones[0].id;
  return null;
}

export function formatMuestraSelectLabel(
  m: MuestraTransaccional,
  tipoMuestraNombre?: string
): string {
  const tipo = tipoMuestraNombre || `tipo #${m.tipo_muestra}`;
  const cont = m.tipo_contenedor != null ? `cont. #${m.tipo_contenedor}` : '';
  const contPart = cont ? ` · ${cont}` : '';
  const code = m.codigo_barra ? ` · ${m.codigo_barra}` : '';
  return `#${m.id}${code} · ${tipo}${contPart} · ${m.estado}`;
}
