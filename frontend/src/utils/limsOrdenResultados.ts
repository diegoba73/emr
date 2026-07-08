import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';

/** True si todos los resultados de la orden tienen valor textual guardado. */
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

export function resultadoTieneValor(r: ResultadoExamenLims): boolean {
  return (r.valor_obtenido ?? '').trim() !== '';
}
