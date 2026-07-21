/** Utilidades: tubos físicos (tope 10/tubo; hemograma = 1 unidad). */

export const MAX_EXAMENES_POR_TUBO = 10;

/** Códigos de componentes PAN_HEMO (alineado a catalogo_solicitud_papel). */
export const CODIGOS_HEMOGRAMA = new Set([
  'HEMATIES',
  'HTO',
  'HGB',
  'RDW',
  'LEU',
  'NEUT_CAY',
  'NEUT_SEG',
  'EOS',
  'BAS',
  'LINF',
  'MONO',
  'PLAQ',
]);

export interface TuboOrdenPreview {
  tipo_muestra_id: number;
  tipo_contenedor_id: number;
  tipo_contenedor_codigo: string;
  tipo_contenedor_nombre: string;
  examenes: string[];
  cantidad: number;
  examenes_count: number;
}

export function cantidadTubosPorExamenes(
  nExamenes: number,
  maxPorTubo: number = MAX_EXAMENES_POR_TUBO
): number {
  if (nExamenes <= 0) return 0;
  return Math.ceil(nExamenes / maxPorTubo);
}

/** Unidades hacia el tope: hemograma completo cuenta 1 aunque tenga N componentes. */
export function unidadesParaCalculoTubos(codigosExamen: string[]): number {
  let tieneHemo = false;
  let otros = 0;
  for (const codigo of codigosExamen) {
    if (CODIGOS_HEMOGRAMA.has(codigo)) {
      tieneHemo = true;
    } else {
      otros += 1;
    }
  }
  return otros + (tieneHemo ? 1 : 0);
}

export function totalEtiquetasDesdeTubos(tubos: TuboOrdenPreview[]): number {
  return tubos.reduce((acc, t) => acc + (t.cantidad || 0), 0);
}

export function formatTuboPreviewLabel(t: TuboOrdenPreview): string {
  const nExam = t.examenes_count ?? t.examenes?.length ?? 0;
  const examTxt =
    nExam === 1
      ? t.examenes[0] || '1 examen'
      : `${nExam} exámenes`;
  return `${t.tipo_contenedor_codigo} ×${t.cantidad} — ${examTxt}`;
}
