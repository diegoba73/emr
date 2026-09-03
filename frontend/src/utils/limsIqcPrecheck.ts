import { postIqcPrecheckBatch } from '../services/limsApi';
import type { PendientePedidoRow } from './limsPendientesUnificados';

/** Enriquece filas LAB_CLINICO con estado IQC (batch). Micro / errores → na. */
export async function attachIqcStatusToRows(rows: PendientePedidoRow[]): Promise<PendientePedidoRow[]> {
  const labIds = rows.filter((r) => r.tipo === 'LAB_CLINICO').map((r) => r.id);
  if (!labIds.length) {
    return rows.map((r) => ({ ...r, iqcStatus: r.iqcStatus ?? 'na' }));
  }
  try {
    const results = await postIqcPrecheckBatch(labIds);
    const byId = new Map(results.map((x) => [x.solicitud_id, x]));
    return rows.map((r) => {
      if (r.tipo !== 'LAB_CLINICO') return { ...r, iqcStatus: 'na' as const };
      const p = byId.get(r.id);
      if (!p || !p.aplicable) return { ...r, iqcStatus: 'na' as const };
      return { ...r, iqcStatus: p.ok ? ('ok' as const) : ('falta' as const) };
    });
  } catch {
    return rows.map((r) => ({ ...r, iqcStatus: r.iqcStatus ?? 'na' }));
  }
}
