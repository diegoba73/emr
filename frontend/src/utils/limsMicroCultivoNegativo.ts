import type { AisladoMicrobiologico, LecturaCultivo } from '../types/lims';

const LAX_SIGNIFICANCIA = new Set(['CONTAMINANTE', 'FLORA_HABITUAL']);

/** Texto base para informe final de cultivo sin desarrollo. */
export const TEXTO_INFORME_FINAL_SIN_DESARROLLO =
  'No se obtuvo desarrollo bacteriano.';

/** Opciones típicas de recuento en urocultivo (UFC/ml). */
export const RECUENTO_BACTERIANO_OPCIONES = [
  '<10³ UFC/ml',
  '10³–10⁴ UFC/ml',
  '10⁴–10⁵ UFC/ml',
  '≥10⁵ UFC/ml',
] as const;

/**
 * ¿Hay al menos una lectura SIN_DESARROLLO y ningún aislado que bloquee
 * la completitud del informe final? (espejo ligero de la regla backend).
 */
export function cultivoNegativoElegibleParaInformeFinal(
  lecturas: LecturaCultivo[],
  aislados: AisladoMicrobiologico[]
): boolean {
  const tieneSinDesarrollo = lecturas.some((l) => l.crecimiento === 'SIN_DESARROLLO');
  if (!tieneSinDesarrollo) return false;
  for (const a of aislados) {
    if (a.estado === 'DESCARTADO') continue;
    if (a.estado === 'SOSPECHADO' && LAX_SIGNIFICANCIA.has(a.significancia || '')) continue;
    if (a.estado === 'SOSPECHADO') return false;
    if (a.estado === 'IDENTIFICADO' && a.requiere_antibiograma) return false;
  }
  return true;
}

/** Todas las lecturas (si hay) son SIN_DESARROLLO. */
export function todasLecturasSinDesarrollo(lecturas: LecturaCultivo[]): boolean {
  return lecturas.length > 0 && lecturas.every((l) => l.crecimiento === 'SIN_DESARROLLO');
}

/** Texto de informe negativo (el recuento va solo en lecturas de cultivo). */
export function textoInformeFinalSinDesarrollo(_lecturas?: LecturaCultivo[]): string {
  return TEXTO_INFORME_FINAL_SIN_DESARROLLO;
}
