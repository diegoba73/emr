/**
 * Validación y payload para carga de resultados LIMS (B2-C).
 * Sin logs de datos sensibles.
 */
import type { CargarResultadoPayload, LimsTipoExamen, MuestraTransaccional, ResultadoExamenLims } from '../types/lims';
import { convertTicketEntry, entryFromStored, usesTicketEntry } from './entradaResultados';
import { calcChcmGdl, calcVcmFl } from './hemogramaIndices';
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
  // Compat: si solo quedó numérico en draft (p. ej. autofill VCM), usarlo como valor.
  if (!valor && vnStr) valor = vnStr;

  const item: CargarResultadoPayload = {
    id: resultadoId,
    valor,
  };

  // Derivar número para flags/tendencias: draft explícito, o Valor si es parseable.
  const vnFromDraft = parseValorNumerico(vnStr);
  if (vnFromDraft !== undefined && typeof vnFromDraft === 'number') {
    item.valor_numerico = vnFromDraft;
  } else {
    const vnFromValor = parseValorNumerico(valor);
    if (vnFromValor !== undefined && typeof vnFromValor === 'number') {
      item.valor_numerico = vnFromValor;
    }
  }

  const unidad = row.unidad.trim();
  if (unidad) item.unidad = unidad;

  if (row.muestra_id != null) {
    item.muestra_id = row.muestra_id;
  }

  return item;
}

/**
 * Mapa codigo→valor clínico para sugerir conclusión con el borrador de pantalla
 * (incluye conversión Sysmex). Si la fila no tiene draft, usa valor ya guardado.
 */
export function buildValoresBorradorConclusion(
  resultados: ResultadoExamenLims[],
  draft: Record<number, DraftCargaRow>,
  catalog: Map<number, LimsTipoExamen>
): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const r of resultados) {
    const te = catalog.get(r.tipo_examen);
    const codigo = (r.tipo_examen_codigo || te?.codigo || '').trim().toUpperCase();
    if (!codigo) continue;

    const row = draft[r.id];
    if (row && draftRowHasValue(row, te, r.tipo_examen_codigo)) {
      const payload = buildCargarResultadoPayload(r.id, row, te, r.tipo_examen_codigo);
      if (payload.valor_numerico !== undefined && payload.valor_numerico !== '') {
        out[codigo] = payload.valor_numerico as string | number;
      } else if (payload.valor?.trim()) {
        out[codigo] = payload.valor.trim();
      }
      continue;
    }

    if (r.valor_numerico != null && String(r.valor_numerico).trim() !== '') {
      out[codigo] = r.valor_numerico as string | number;
    } else if ((r.valor_obtenido || '').trim()) {
      out[codigo] = (r.valor_obtenido || '').trim();
    }
  }
  return out;
}

/** Valor clínico numérico desde draft (Sysmex o estándar) para un resultado. */
export function draftValorClinicoNumerico(
  r: ResultadoExamenLims,
  draft: Record<number, DraftCargaRow>,
  catalog: Map<number, LimsTipoExamen>
): number | null {
  const te = catalog.get(r.tipo_examen);
  const row = draft[r.id];
  if (row && draftRowHasValue(row, te, r.tipo_examen_codigo)) {
    const payload = buildCargarResultadoPayload(r.id, row, te, r.tipo_examen_codigo);
    if (payload.valor_numerico !== undefined && payload.valor_numerico !== '') {
      const n = Number(payload.valor_numerico);
      return Number.isFinite(n) ? n : null;
    }
    const n = Number(payload.valor);
    return Number.isFinite(n) ? n : null;
  }
  if (r.valor_numerico != null && String(r.valor_numerico).trim() !== '') {
    const n = Number(r.valor_numerico);
    return Number.isFinite(n) ? n : null;
  }
  const n = Number((r.valor_obtenido || '').trim());
  return Number.isFinite(n) ? n : null;
}

function patchIndiceTicket(
  draft: Record<number, DraftCargaRow>,
  r: ResultadoExamenLims,
  catalog: Map<number, LimsTipoExamen>,
  clinical: number,
  manualIds: ReadonlySet<number>
): Record<number, DraftCargaRow> {
  if (manualIds.has(r.id)) return draft;
  const te = catalog.get(r.tipo_examen);
  const row = draft[r.id] || {
    valor: '',
    valor_sysmex: '',
    valor_numerico: '',
    unidad: '',
    muestra_id: null,
  };
  const ticket = entryFromStored(te, clinical, r.tipo_examen_codigo);
  if (!ticket) return draft;
  const conv = convertTicketEntry(te, ticket, r.tipo_examen_codigo);
  const unidad =
    row.unidad.trim() ||
    te?.unidad_default?.trim() ||
    getSysmexUnidad(r.tipo_examen_codigo || te?.codigo) ||
    '';
  return {
    ...draft,
    [r.id]: {
      ...row,
      valor_sysmex: ticket,
      valor: conv?.valorInforme ?? String(clinical),
      valor_numerico: conv ? String(conv.valorNumerico) : String(clinical),
      unidad,
    },
  };
}

/**
 * Rellena VCM/CHCM (si no fueron editados a mano) desde Hematíes/HTO/HGB.
 */
export function applyAutofillVcmChcm(
  resultados: ResultadoExamenLims[],
  draft: Record<number, DraftCargaRow>,
  catalog: Map<number, LimsTipoExamen>,
  manualIds: ReadonlySet<number>
): Record<number, DraftCargaRow> {
  const byCodigo = new Map<string, ResultadoExamenLims>();
  for (const r of resultados) {
    const te = catalog.get(r.tipo_examen);
    const c = (r.tipo_examen_codigo || te?.codigo || '').trim().toUpperCase();
    if (c) byCodigo.set(c, r);
  }
  const rHgb = byCodigo.get('HGB');
  const rHto = byCodigo.get('HTO');
  const rRbc = byCodigo.get('HEMATIES');
  const rVcm = byCodigo.get('VCM');
  const rChcm = byCodigo.get('CHCM');
  if (!rHgb || !rHto || !rRbc || (!rVcm && !rChcm)) return draft;

  const hgb = draftValorClinicoNumerico(rHgb, draft, catalog);
  const hto = draftValorClinicoNumerico(rHto, draft, catalog);
  const rbc = draftValorClinicoNumerico(rRbc, draft, catalog);
  if (hgb == null || hto == null || rbc == null) return draft;

  let next = draft;
  const vcm = calcVcmFl(hto, rbc);
  if (rVcm && vcm != null) {
    next = patchIndiceTicket(next, rVcm, catalog, vcm, manualIds);
  }
  const chcm = calcChcmGdl(hgb, hto);
  if (rChcm && chcm != null) {
    next = patchIndiceTicket(next, rChcm, catalog, chcm, manualIds);
  }
  return next;
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
