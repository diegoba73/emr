import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';

/** True si todos los resultados de la orden tienen valor informado (texto/símbolos). */
export function ordenResultadosCompletos(orden: SolicitudExamenLims): boolean {
  const resultados = orden.resultados || [];
  if (resultados.length === 0) return false;
  return resultados.every((r) => resultadoTieneValor(r));
}

export function countResultadosConValor(orden: SolicitudExamenLims): { conValor: number; total: number } {
  const resultados = orden.resultados || [];
  const total = resultados.length;
  const conValor = resultados.filter((r) => resultadoTieneValor(r)).length;
  return { conValor, total };
}

/**
 * SoT de “informado”: `valor_obtenido` (números, texto o símbolos: Positivo, <0.5, etc.).
 * No usa `valor_numerico` solo: eso es auxiliar para rangos/tendencias y no sustituye
 * un cualitativo vacío.
 */
export function resultadoTieneValor(
  r: Pick<ResultadoExamenLims, 'valor_obtenido' | 'valor_numerico'>
): boolean {
  return (r.valor_obtenido ?? '').trim() !== '';
}

/**
 * Texto a mostrar en la grilla de carga.
 * Prioriza valor_obtenido (texto/símbolos); solo si está vacío y hay un número finito
 * en valor_numerico, lo usa como respaldo visual (legacy / solo-numérico).
 */
export function valorTextoDesdeResultado(
  r: Pick<ResultadoExamenLims, 'valor_obtenido' | 'valor_numerico'>
): string {
  const texto = (r.valor_obtenido ?? '').trim();
  if (texto) return texto;
  if (r.valor_numerico == null || String(r.valor_numerico).trim() === '') return '';
  const n = Number(r.valor_numerico);
  if (!Number.isFinite(n)) return '';
  return String(r.valor_numerico);
}
